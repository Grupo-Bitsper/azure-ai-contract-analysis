"""
Exploración read-only de los 2 sites ROCA para identificar carpetas con PDFs no
muestreadas todavía por Fase 4A. Genera un reporte stdout con conteos para
decidir qué incluir en la ampliación de la muestra.

Uso: `python explore_sharepoint_folders.py`
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from download_sample_pdfs import (  # reusa auth + helpers
    get_sync_agent_secret,
    get_graph_token,
    graph_get,
    list_children,
    SHAREPOINT_HOST,
    SITE_1_NAME,
    SITE_2_NAME,
    MAX_FILE_SIZE_BYTES,
)


def count_pdfs_recursive(
    token: str, drive_id: str, folder_id: str, depth: int = 0, max_depth: int = 3
) -> tuple[int, float]:
    """Cuenta PDFs elegibles recursivamente. Retorna (count, size_MB)."""
    if depth > max_depth:
        return (0, 0.0)
    try:
        children = list_children(token, drive_id, folder_id)
    except Exception:
        return (0, 0.0)
    count = 0
    size_mb = 0.0
    for c in children:
        if "folder" in c:
            sub_count, sub_size = count_pdfs_recursive(token, drive_id, c["id"], depth + 1, max_depth)
            count += sub_count
            size_mb += sub_size
            continue
        fi = c.get("file") or {}
        if fi.get("mimeType") != "application/pdf":
            continue
        s = c.get("size", 0)
        if 0 < s <= MAX_FILE_SIZE_BYTES:
            count += 1
            size_mb += s / (1024 * 1024)
    return (count, size_mb)


def summarize_folder(
    token: str, drive_id: str, folder_id: str, folder_name: str, already_sampled: set[str], indent: str = "  "
) -> None:
    """Cuenta PDFs directos + recursivos y reporta."""
    try:
        children = list_children(token, drive_id, folder_id)
    except Exception as e:
        print(f"{indent}[{folder_name}] error listando: {e}")
        return

    direct_pdfs_eligible = 0
    subfolders: list[dict] = []
    direct_size_mb = 0.0

    for c in children:
        if "folder" in c:
            subfolders.append(c)
            continue
        fi = c.get("file") or {}
        if fi.get("mimeType") != "application/pdf":
            continue
        size = c.get("size", 0)
        if 0 < size <= MAX_FILE_SIZE_BYTES:
            direct_pdfs_eligible += 1
            direct_size_mb += size / (1024 * 1024)

    total_recursive, total_size_mb = count_pdfs_recursive(token, drive_id, folder_id)

    marker = " ⭐ YA MUESTREADA" if folder_name in already_sampled else ""
    print(
        f"{indent}📁 {folder_name}{marker}  "
        f"[directos={direct_pdfs_eligible}, recursivos_total={total_recursive}, "
        f"size_total={total_size_mb:.0f} MB, subfolders={len(subfolders)}]"
    )
    # listar subcarpetas si hay pocas (≤8) y el usuario no la ha muestreado
    if subfolders and len(subfolders) <= 10:
        for sub in subfolders:
            sub_name = sub.get("name", "")
            sub_count, sub_size = count_pdfs_recursive(token, drive_id, sub["id"])
            print(f"{indent}    └─ {sub_name}  [recursivo={sub_count} PDFs, {sub_size:.0f} MB]")


def explore_drive(token: str, drive: dict, already_sampled: set[str]) -> None:
    drive_name = drive.get("name", "?")
    drive_id = drive["id"]
    print(f"\n  ▶ Drive: {drive_name}")

    try:
        root_children = graph_get(
            token,
            f"/drives/{drive_id}/root/children",
            params={"$top": "200"},
        ).get("value", [])
    except Exception as e:
        print(f"    ! error listando root: {e}")
        return

    if not root_children:
        print("    (vacío)")
        return

    for item in root_children:
        name = item.get("name", "")
        if "folder" in item:
            summarize_folder(token, drive_id, item["id"], name, already_sampled, indent="    ")
        elif "file" in item:
            mime = (item.get("file") or {}).get("mimeType", "")
            if mime == "application/pdf":
                size_mb = item.get("size", 0) / (1024 * 1024)
                print(f"    📄 {name} ({size_mb:.1f} MB PDF suelto)")


def explore_site(token: str, site_name: str, already_sampled: set[str]) -> None:
    print(f"\n{'=' * 72}")
    print(f"=== Site: {site_name} ===")
    print(f"{'=' * 72}")
    site = graph_get(token, f"/sites/{SHAREPOINT_HOST}:/sites/{site_name}")
    site_id = site["id"]

    drives = graph_get(token, f"/sites/{site_id}/drives").get("value", [])
    print(f"  drives disponibles: {len(drives)}")
    for d in drives:
        print(f"    - {d.get('name')} ({d.get('driveType')})")

    for d in drives:
        if d.get("driveType") != "documentLibrary":
            continue
        explore_drive(token, d, already_sampled)


def main() -> int:
    print("Exploración de carpetas SharePoint para ampliación de muestra Fase 4A")
    print("=" * 72)

    secret = get_sync_agent_secret()
    token = get_graph_token(secret)

    site_1_sampled = {
        "07. Permisos de construcción",
        "11. Estudio fase I - Ambiental",
        "30. Contrato de arrendamiento y anexos",
        "33. Constancia situacion fiscal",
        "65. Planos arquitectonicos (As built)",
    }
    site_2_sampled = {"FESWORLD"}

    explore_site(token, SITE_1_NAME, site_1_sampled)
    explore_site(token, SITE_2_NAME, site_2_sampled)

    print("\n=== Fin ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
