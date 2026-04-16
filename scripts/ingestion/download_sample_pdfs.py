"""
Fase 4A.1 — Descarga automatizada de muestra representativa de PDFs desde SharePoint.

Autentica el sync robot `roca-copilot-sync-agent` con client_credentials (secret
leído del Key Vault `kv-roca-copilot-prod`) y baja 15-22 PDFs representativos de
carpetas canónicas de los dos sites de ROCA directo a `contratosdemo_real/`.

Es one-shot e idempotente: re-correr salta archivos ya presentes. Naming convention
`{site}__{carpeta}__{archivo_original}.pdf` preserva la taxonomía origen para que
el discovery pueda relacionar cada PDF con su carpeta canónica.
"""

from __future__ import annotations

import os
import random
import re
import sys
from pathlib import Path

import requests
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

# --- Constants (single source of truth — do NOT parametrize) -----------------

TENANT_ID = "9015a126-356b-4c63-9d1f-d2138ca83176"
SYNC_AGENT_APP_ID = "18884cef-ace3-4899-9a54-be7eb66587b7"
KEY_VAULT_URI = "https://kv-roca-copilot-prod.vault.azure.net/"
KV_SECRET_NAME = "roca-copilot-sync-agent-secret"

SHAREPOINT_HOST = "rocadesarrollos1.sharepoint.com"  # con el "1" — memoria project_roca_sharepoint_hostname
SITE_1_NAME = "ROCA-IAInmuebles"
SITE_2_NAME = "ROCAIA-INMUEBLESV2"

# Cada entrada es una "fuente" de muestreo: (site, drive, folder_name_or_None, n_pdfs).
# - folder_name=None significa "raíz del drive" (los PDFs sueltos, sin recursión).
# - folder_name="X" significa "carpeta X dentro del drive, recorrer recursivamente".
# Muestra ampliada 2026-04-15 para reducir sesgo — ver `FASE_4A_DISCOVERY_REPORT.md`.
SAMPLE_SOURCES: list[tuple[str, str, str | None, int]] = [
    # Site 1 - drive principal "Documentos"
    (SITE_1_NAME, "Documentos", "07. Permisos de construcción", 3),
    (SITE_1_NAME, "Documentos", "11. Estudio fase I - Ambiental", 3),
    (SITE_1_NAME, "Documentos", "30. Contrato de arrendamiento y anexos", 4),
    (SITE_1_NAME, "Documentos", "33. Constancia situacion fiscal", 3),
    (SITE_1_NAME, "Documentos", "65. Planos arquitectonicos (As built)", 3),
    (SITE_1_NAME, "Documentos", "Principal", 2),
    # Site 1 - drive "Biblioteca de suspensiones de conservación" (PDFs sueltos en root)
    (SITE_1_NAME, "Biblioteca de suspensiones de conservación", None, 12),
    # Site 1 - drive "Documentos semantica copilot" (1 PDF suelto)
    (SITE_1_NAME, "Documentos semantica copilot", None, 1),
    # Site 2 - drive principal "Documentos", carpeta FESWORLD con 6 proyectos
    (SITE_2_NAME, "Documentos", "FESWORLD", 8),
]

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # skip >50 MB
RANDOM_SEED = 42
MAX_RECURSION_DEPTH = 4  # profundidad de búsqueda dentro de cada carpeta canónica

TARGET_DIR = Path("/Users/datageni/Documents/ai_azure/contratosdemo_real")

GRAPH_BASE = "https://graph.microsoft.com/v1.0"

# --- Auth --------------------------------------------------------------------


def get_sync_agent_secret() -> str:
    """Lee el secret del sync robot desde el Key Vault usando DefaultAzureCredential."""
    cred = DefaultAzureCredential()
    client = SecretClient(vault_url=KEY_VAULT_URI, credential=cred)
    return client.get_secret(KV_SECRET_NAME).value


def get_graph_token(client_secret: str) -> str:
    """client_credentials flow contra Entra ID para scope Graph."""
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    resp = requests.post(
        url,
        data={
            "grant_type": "client_credentials",
            "client_id": SYNC_AGENT_APP_ID,
            "client_secret": client_secret,
            "scope": "https://graph.microsoft.com/.default",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


# --- Graph helpers -----------------------------------------------------------


def graph_get(token: str, path: str, params: dict | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{GRAPH_BASE}{path}", headers=headers, params=params, timeout=60)
    if not resp.ok:
        print(f"  ! Graph error {resp.status_code}: {resp.text[:300]}", file=sys.stderr)
        resp.raise_for_status()
    return resp.json()


def get_site_id(token: str, site_name: str) -> str:
    data = graph_get(token, f"/sites/{SHAREPOINT_HOST}:/sites/{site_name}")
    return data["id"]


def get_default_drive_id(token: str, site_id: str) -> str:
    """Retorna el drive marcado como documentLibrary 'Documentos' (library principal)."""
    return get_drive_id_by_name(token, site_id, "Documentos")


def get_drive_id_by_name(token: str, site_id: str, drive_name: str) -> str:
    """Retorna el drive con el nombre exacto `drive_name`."""
    data = graph_get(token, f"/sites/{site_id}/drives")
    for d in data.get("value", []):
        if d.get("name") == drive_name:
            return d["id"]
    # fallback: el primer documentLibrary
    for d in data.get("value", []):
        if d.get("driveType") == "documentLibrary":
            return d["id"]
    raise RuntimeError(f"No drive '{drive_name}' en site {site_id}")


def collect_pdfs_root_only(token: str, drive_id: str) -> list[tuple[dict, str]]:
    """Lista PDFs sueltos en la raíz del drive (sin recursión). Útil para drives
    que son repositorios planos de archivos como 'Biblioteca de suspensiones...'."""
    results: list[tuple[dict, str]] = []
    data = graph_get(token, f"/drives/{drive_id}/root/children", params={"$top": "200"})
    for item in data.get("value", []):
        if "folder" in item:
            continue
        fi = item.get("file") or {}
        if fi.get("mimeType") != "application/pdf":
            continue
        size = item.get("size", 0)
        if size <= 0 or size > MAX_FILE_SIZE_BYTES:
            continue
        results.append((item, ""))  # rel_path vacío = root
    return results


def find_folder_item_id(token: str, drive_id: str, folder_name: str) -> str | None:
    """Busca `folder_name` en la raíz del drive. Retorna None si no existe."""
    data = graph_get(token, f"/drives/{drive_id}/root/children", params={"$top": "200"})
    for item in data.get("value", []):
        if item.get("name") == folder_name and "folder" in item:
            return item["id"]
    return None


def list_children(token: str, drive_id: str, item_id: str) -> list[dict]:
    """Lista hijos de un item (paginando)."""
    results: list[dict] = []
    url = f"/drives/{drive_id}/items/{item_id}/children"
    params: dict[str, str] | None = {"$top": "200"}
    while True:
        data = graph_get(token, url, params=params)
        results.extend(data.get("value", []))
        next_link = data.get("@odata.nextLink")
        if not next_link:
            break
        url = next_link.replace(GRAPH_BASE, "")
        params = None
    return results


def collect_pdfs_recursive(
    token: str,
    drive_id: str,
    folder_item_id: str,
    rel_path: str = "",
    depth: int = 0,
) -> list[tuple[dict, str]]:
    """Recorre recursivamente un folder. Retorna lista de (item, rel_path_desde_canonical)."""
    if depth > MAX_RECURSION_DEPTH:
        return []

    results: list[tuple[dict, str]] = []
    children = list_children(token, drive_id, folder_item_id)

    for child in children:
        child_name = child.get("name", "")
        if "folder" in child:
            sub_rel = f"{rel_path}/{child_name}" if rel_path else child_name
            results.extend(
                collect_pdfs_recursive(token, drive_id, child["id"], sub_rel, depth + 1)
            )
            continue

        file_info = child.get("file") or {}
        mime = file_info.get("mimeType", "")
        size = child.get("size", 0)

        if mime != "application/pdf":
            continue
        if size <= 0 or size > MAX_FILE_SIZE_BYTES:
            continue

        results.append((child, rel_path))

    return results


def download_file(token: str, drive_id: str, item_id: str, target_path: Path) -> None:
    """Descarga por streaming (chunks de 1 MB)."""
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{GRAPH_BASE}/drives/{drive_id}/items/{item_id}/content"
    with requests.get(url, headers=headers, stream=True, timeout=300) as resp:
        resp.raise_for_status()
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    fh.write(chunk)


# --- Naming ------------------------------------------------------------------

_SLUG_RE = re.compile(r"[^a-zA-Z0-9._-]+")


def slugify(text: str) -> str:
    return _SLUG_RE.sub("_", text).strip("_")


def make_target_filename(site: str, folder: str, rel_path: str, original: str) -> str:
    parts = [slugify(site), slugify(folder)]
    if rel_path:
        parts.append(slugify(rel_path))
    parts.append(slugify(original))
    return "__".join(parts)


# --- Main per-site workflow --------------------------------------------------


def sample_from_source(
    token: str,
    site_name: str,
    drive_name: str,
    folder_name: str | None,
    n: int,
    rng: random.Random,
    site_cache: dict[str, str],
    drive_cache: dict[tuple[str, str], str],
) -> tuple[int, int]:
    """Descarga `n` PDFs de una fuente (site+drive+folder o root). Retorna (dl, skipped)."""
    src_label = f"{drive_name}" + (f" / {folder_name}" if folder_name else " / <root>")
    print(f"\n  → {src_label}")

    # cache site_id
    if site_name not in site_cache:
        site_cache[site_name] = get_site_id(token, site_name)
    site_id = site_cache[site_name]

    # cache drive_id
    cache_key = (site_name, drive_name)
    if cache_key not in drive_cache:
        drive_cache[cache_key] = get_drive_id_by_name(token, site_id, drive_name)
    drive_id = drive_cache[cache_key]

    # listar PDFs elegibles según el tipo de fuente
    if folder_name is None:
        pdfs = collect_pdfs_root_only(token, drive_id)
    else:
        folder_id = find_folder_item_id(token, drive_id, folder_name)
        if not folder_id:
            print("    [skip] carpeta no encontrada en raíz del drive")
            return (0, 0)
        pdfs = collect_pdfs_recursive(token, drive_id, folder_id)

    print(f"    {len(pdfs)} PDFs elegibles (<=50MB)")
    if not pdfs:
        return (0, 0)

    # sample determinístico
    pdfs.sort(key=lambda pair: pair[0]["id"])
    sample = rng.sample(pdfs, k=min(n, len(pdfs)))

    # etiqueta canónica para el naming (para root usamos el nombre del drive)
    canonical_label = folder_name if folder_name else drive_name

    downloaded = 0
    skipped = 0
    for item, rel_path in sample:
        target_name = make_target_filename(site_name, canonical_label, rel_path, item["name"])
        target_path = TARGET_DIR / target_name
        size_mb = item.get("size", 0) / (1024 * 1024)

        if target_path.exists():
            print(f"    [skip-existe] {target_name} ({size_mb:.1f} MB)")
            skipped += 1
            continue

        try:
            print(f"    [bajando]    {target_name} ({size_mb:.1f} MB)")
            download_file(token, drive_id, item["id"], target_path)
            downloaded += 1
        except requests.HTTPError as e:
            print(f"    [error] {target_name}: {e}")

    return downloaded, skipped


def main() -> int:
    print("Fase 4A.1 — Descarga de muestra representativa de PDFs reales")
    print(f"  target dir: {TARGET_DIR}")
    print(f"  fuentes de muestreo: {len(SAMPLE_SOURCES)}")
    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    print("\n[1/3] Leyendo secret del sync robot desde Key Vault...")
    secret = get_sync_agent_secret()

    print("[2/3] Obteniendo token Graph con client_credentials...")
    token = get_graph_token(secret)

    print("[3/3] Recorriendo fuentes y descargando...")
    rng = random.Random(RANDOM_SEED)

    site_cache: dict[str, str] = {}
    drive_cache: dict[tuple[str, str], str] = {}

    # agrupar por site para output legible
    current_site = None
    total_dl = 0
    total_skipped = 0

    for site_name, drive_name, folder_name, n in SAMPLE_SOURCES:
        if site_name != current_site:
            print(f"\n=== Site: {site_name} ===")
            current_site = site_name
        dl, sk = sample_from_source(
            token, site_name, drive_name, folder_name, n, rng, site_cache, drive_cache
        )
        total_dl += dl
        total_skipped += sk

    total_pdfs = sum(1 for p in TARGET_DIR.iterdir() if p.suffix.lower() == ".pdf")
    print("\n=== Resumen ===")
    print(f"  descargados en esta corrida: {total_dl}")
    print(f"  ya existentes (skipped):     {total_skipped}")
    print(f"  total PDFs en {TARGET_DIR.name}: {total_pdfs}")

    if total_pdfs < 15:
        print(f"\n  ⚠ advertencia: sólo {total_pdfs} PDFs (target mínimo 15)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
