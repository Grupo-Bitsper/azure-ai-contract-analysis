"""Microsoft Graph client — app-only auth via the sync robot App Registration.

Covers:
- Site + drive discovery by name
- File download by item id
- Delta query for incremental change tracking per drive
- Permission extraction for a drive item
- SharePoint group member expansion (for security trimming)
"""

from __future__ import annotations

from typing import Iterator

import requests

from . import auth, config

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
REQUEST_TIMEOUT = 60


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {auth.get_graph_token()}"}


def _get(path: str, params: dict | None = None) -> dict:
    url = path if path.startswith("http") else f"{GRAPH_BASE}{path}"
    resp = requests.get(url, headers=_headers(), params=params, timeout=REQUEST_TIMEOUT)
    if not resp.ok:
        raise RuntimeError(f"Graph GET {path} failed {resp.status_code}: {resp.text[:500]}")
    return resp.json()


# --- Site + drive discovery ---


def get_site_id(site_name: str) -> str:
    data = _get(f"/sites/{config.SP_HOSTNAME}:/sites/{site_name}")
    return data["id"]


def get_default_drive_id(site_id: str) -> str:
    """Returns the id of the `Documentos` document library (default drive) of a site."""
    data = _get(f"/sites/{site_id}/drives")
    for d in data.get("value", []):
        if d.get("name") == "Documentos":
            return d["id"]
    for d in data.get("value", []):
        if d.get("driveType") == "documentLibrary":
            return d["id"]
    raise RuntimeError(f"No document library drive found for site {site_id}")


# --- File content + metadata ---


def get_item(drive_id: str, item_id: str) -> dict:
    return _get(f"/drives/{drive_id}/items/{item_id}")


def download_item_bytes(drive_id: str, item_id: str) -> bytes:
    url = f"{GRAPH_BASE}/drives/{drive_id}/items/{item_id}/content"
    resp = requests.get(url, headers=_headers(), timeout=300)
    resp.raise_for_status()
    return resp.content


def stream_download_to_temp(drive_id: str, item_id: str) -> tuple[str, str]:
    """Streams a Graph drive item to /tmp in 64KB chunks, computing MD5 simultaneously.
    Returns (tmp_path, content_hash). Max RAM at any point: 64KB, not the full file size.
    Caller MUST call os.unlink(tmp_path) when done (use try/finally)."""
    import hashlib
    import os
    import tempfile

    url = f"{GRAPH_BASE}/drives/{drive_id}/items/{item_id}/content"
    md5 = hashlib.md5()
    fd, tmp_path = tempfile.mkstemp(suffix=".pdf", dir="/tmp")
    try:
        with requests.get(url, headers=_headers(), stream=True, timeout=300) as resp:
            resp.raise_for_status()
            with os.fdopen(fd, "wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    md5.update(chunk)
                    f.write(chunk)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    return tmp_path, md5.hexdigest()


# --- Delta query for incremental sync ---


def delta_page(drive_id: str, delta_link: str | None) -> dict:
    """Fetches one page of the delta feed. If `delta_link` is None, starts
    from the current state. Returns the full response including @odata.nextLink
    and/or @odata.deltaLink."""
    if delta_link:
        return _get(delta_link)
    return _get(f"/drives/{drive_id}/root/delta")


def iter_delta_changes(drive_id: str, delta_link: str | None) -> Iterator[dict]:
    """Iterates all delta-changed items across pages. Yields items. The final
    deltaLink is stashed on the last-yielded item under __final_delta_link__
    so the caller can persist it. (We don't return a tuple to keep the API
    stream-friendly.)"""
    next_link: str | None = delta_link
    final_delta: str | None = None
    while True:
        data = delta_page(drive_id, next_link)
        for item in data.get("value", []):
            yield item
        next_link = data.get("@odata.nextLink")
        final_delta = data.get("@odata.deltaLink") or final_delta
        if not next_link:
            break
    if final_delta:
        yield {"__final_delta_link__": final_delta}


# --- Permissions (ACL extraction) ---


def get_item_permissions(site_id: str, list_id: str, list_item_id: str) -> dict:
    return _get(f"/sites/{site_id}/lists/{list_id}/items/{list_item_id}/permissions")


def get_sharepoint_group_members(site_id: str, group_id: str) -> list[dict]:
    data = _get(f"/sites/{site_id}/groups/{group_id}/members")
    return data.get("value", [])


def list_drive_items_recursive(drive_id: str, folder_id: str = "root", max_items: int = 5000) -> Iterator[dict]:
    """BFS traversal of a drive. Used by the full resync workflow to enumerate
    every file in a site. Skips folders, yields only files."""
    queue: list[str] = [folder_id]
    count = 0
    while queue and count < max_items:
        current = queue.pop(0)
        url = f"/drives/{drive_id}/items/{current}/children" if current != "root" else f"/drives/{drive_id}/root/children"
        next_url: str | None = url
        params: dict | None = {"$top": "200"}
        while next_url:
            data = _get(next_url, params=params)
            for item in data.get("value", []):
                if "folder" in item:
                    queue.append(item["id"])
                    continue
                file_info = item.get("file") or {}
                if file_info.get("mimeType") == "application/pdf":
                    yield item
                    count += 1
                    if count >= max_items:
                        return
            next_link = data.get("@odata.nextLink")
            if not next_link:
                break
            next_url = next_link
            params = None
