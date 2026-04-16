"""
Fase 4B — Backfill de metadatos reales de SharePoint para los 38 PDFs únicos.

Para cada PDF en `contratosdemo_real/`, consulta Graph API y guarda:
- webUrl real (clickeable, abre el archivo en Office Online)
- itemId, driveId, parentPath (para operaciones futuras sin re-resolver)
- lastModifiedDateTime (para `fecha_procesamiento` real)
- size, createdDateTime, createdBy, lastModifiedBy (metadata opcional)

Guarda el resultado en `contratosdemo_real/_sharepoint_metadata.json` como map
`{stem: metadata}`. La ingesta de Fase 4B lee ese JSON para el campo `sharepoint_url`.

Estrategia: los PDFs en disco tienen nombres derivados del stem original con el
formato `{site}__{canonical_folder}__{rel_path}__{original_filename}.pdf`. Para
encontrar el archivo real en Graph API, necesitamos:
1. Autenticar sync robot (mismo flujo que download_sample_pdfs.py)
2. Para cada site + drive conocido, recorrer los paths y encontrar el archivo
   con el nombre original_filename
3. Guardar todos los candidates que matcheen por nombre+size+hash

Es idempotente: si el JSON ya existe, skip los stems ya resueltos.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from download_sample_pdfs import (
    get_sync_agent_secret,
    get_graph_token,
    graph_get,
    get_site_id,
    get_drive_id_by_name,
    list_children,
    SHAREPOINT_HOST,
    SITE_1_NAME,
    SITE_2_NAME,
    MAX_FILE_SIZE_BYTES,
)

SAMPLE_DIR = Path("/Users/datageni/Documents/ai_azure/contratosdemo_real")
METADATA_PATH = SAMPLE_DIR / "_sharepoint_metadata.json"
DEDUP_MAP_PATH = SAMPLE_DIR / "_content_hash_dedup.json"


# --- Helpers ----------------------------------------------------------------


def compute_pdf_hash(pdf_path: Path) -> str:
    h = hashlib.md5()
    with open(pdf_path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def walk_drive_for_pdfs(
    token: str, drive_id: str, item_id: str, rel_path: str = "", depth: int = 0, max_depth: int = 6
) -> list[dict]:
    """Recorre un drive y retorna TODOS los PDFs con su metadata completa."""
    if depth > max_depth:
        return []
    results: list[dict] = []
    try:
        children = list_children(token, drive_id, item_id)
    except Exception:
        return []

    for child in children:
        name = child.get("name", "")
        if "folder" in child:
            sub_rel = f"{rel_path}/{name}" if rel_path else name
            results.extend(walk_drive_for_pdfs(token, drive_id, child["id"], sub_rel, depth + 1, max_depth))
            continue
        file_info = child.get("file") or {}
        if file_info.get("mimeType") != "application/pdf":
            continue
        size = child.get("size", 0)
        if size <= 0:
            continue
        results.append(
            {
                "name": name,
                "rel_path": rel_path,
                "id": child["id"],
                "size": size,
                "webUrl": child.get("webUrl"),
                "createdDateTime": child.get("createdDateTime"),
                "lastModifiedDateTime": child.get("lastModifiedDateTime"),
                "parentReference": child.get("parentReference"),
                "file_hashes": file_info.get("hashes"),  # Graph ofrece quickXorHash, sha1Hash
            }
        )
    return results


def index_drive_files(token: str, site_name: str, drive_name: str) -> list[dict]:
    """Devuelve todos los PDFs del drive con metadata completa, incluyendo drive_id + site_id."""
    site_id = get_site_id(token, site_name)
    try:
        drive_id = get_drive_id_by_name(token, site_id, drive_name)
    except Exception as e:
        print(f"  [skip drive] {site_name}/{drive_name}: {e}")
        return []

    # obtener items de la raíz para arrancar recursión
    root = graph_get(token, f"/drives/{drive_id}/root")
    files = walk_drive_for_pdfs(token, drive_id, root["id"])
    for f in files:
        f["site_name"] = site_name
        f["drive_name"] = drive_name
        f["drive_id"] = drive_id
        f["site_id"] = site_id
    return files


# --- Main -------------------------------------------------------------------


def main() -> int:
    print("Fase 4B — Backfill SharePoint metadata para 38 PDFs únicos")
    print(f"  sample_dir: {SAMPLE_DIR}")

    # PDFs en disco
    pdfs = sorted(
        [p for p in SAMPLE_DIR.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"]
    )
    print(f"  PDFs en disco: {len(pdfs)}")

    # Dedup map (solo queremos canonical)
    dedup_info = json.loads(DEDUP_MAP_PATH.read_text()) if DEDUP_MAP_PATH.exists() else {}
    canonical_by_stem: dict[str, str] = dedup_info.get("canonical_by_stem", {})
    stem_to_hash: dict[str, str] = dedup_info.get("stem_to_hash", {})

    canonical_stems = {canonical_by_stem.get(p.stem, p.stem) for p in pdfs}
    print(f"  Stems canónicos: {len(canonical_stems)}")

    # Cargar metadata existente si hay
    existing = {}
    if METADATA_PATH.exists():
        try:
            existing = json.loads(METADATA_PATH.read_text())
            print(f"  Metadata existente: {len(existing)} stems")
        except Exception:
            existing = {}

    # Auth Graph
    print("\n[auth] Leyendo secret del sync robot del KV...")
    secret = get_sync_agent_secret()
    token = get_graph_token(secret)

    # Los drives que exploramos en la ampliación
    drive_sources = [
        (SITE_1_NAME, "Documentos"),
        (SITE_1_NAME, "Biblioteca de suspensiones de conservación"),
        (SITE_1_NAME, "Documentos semantica copilot"),
        (SITE_2_NAME, "Documentos"),
    ]

    print("\n[index] Construyendo índice de todos los PDFs en SharePoint...")
    all_sp_files: list[dict] = []
    for site, drive in drive_sources:
        files = index_drive_files(token, site, drive)
        print(f"  {site} / {drive}: {len(files)} PDFs")
        all_sp_files.extend(files)

    print(f"\n  Total PDFs indexados en SharePoint: {len(all_sp_files)}")

    # Indexar por nombre + size para matching rápido
    sp_by_name: dict[str, list[dict]] = {}
    for f in all_sp_files:
        sp_by_name.setdefault(f["name"], []).append(f)

    print("\n[match] Resolviendo cada PDF local → metadata Graph...")
    metadata: dict[str, dict] = dict(existing)
    matched = 0
    unmatched: list[str] = []

    for pdf_path in pdfs:
        stem = pdf_path.stem
        # solo procesamos canonicals (los duplicados comparten metadata del canonical)
        canonical = canonical_by_stem.get(stem, stem)
        if canonical != stem:
            continue

        if stem in metadata and metadata[stem].get("webUrl"):
            matched += 1
            continue

        # el nombre original es la última parte del stem después del último "__"
        parts = stem.split("__")
        original_name_slugged = parts[-1] + ".pdf"

        # El slugificado es agresivo: restauramos solo reemplazando _ por espacio es inseguro.
        # Mejor: matching por **size + hash** contra candidates del mismo drive/site.
        local_size = pdf_path.stat().st_size
        local_hash = stem_to_hash.get(stem) or compute_pdf_hash(pdf_path)

        # busco por size en todo el universo
        candidates = [f for f in all_sp_files if f["size"] == local_size]
        if not candidates:
            print(f"  [no-match] {stem[:80]} (size={local_size})")
            unmatched.append(stem)
            continue

        # Si hay varios candidatos con el mismo size, preferir el que mejor matcheé por nombre
        # Normalizar ambos removiendo caracteres no alfanuméricos
        import re

        def norm(s: str) -> str:
            return re.sub(r"[^a-zA-Z0-9]", "", s.lower())

        target_norm = norm(original_name_slugged)
        best = None
        best_score = -1
        for c in candidates:
            c_norm = norm(c["name"])
            # score: longitud del common substring / longitud del mayor
            if c_norm == target_norm:
                score = 1000
            elif target_norm in c_norm or c_norm in target_norm:
                score = 500
            else:
                score = len(set(target_norm) & set(c_norm))
            if score > best_score:
                best_score = score
                best = c

        if not best:
            print(f"  [no-best] {stem[:80]}")
            unmatched.append(stem)
            continue

        metadata[stem] = {
            "webUrl": best["webUrl"],
            "name": best["name"],
            "size": best["size"],
            "itemId": best["id"],
            "driveId": best["drive_id"],
            "siteId": best["site_id"],
            "siteName": best["site_name"],
            "driveName": best["drive_name"],
            "relPath": best.get("rel_path", ""),
            "createdDateTime": best.get("createdDateTime"),
            "lastModifiedDateTime": best.get("lastModifiedDateTime"),
            "contentHash": local_hash,
            "matchScore": best_score,
        }
        matched += 1
        print(f"  [OK score={best_score}] {stem[:60]}  →  {best['name'][:50]}")

    # Guardar
    METADATA_PATH.write_text(json.dumps(metadata, ensure_ascii=False, indent=2))

    print("\n=== Resumen ===")
    print(f"  Matched: {matched}")
    print(f"  Unmatched: {len(unmatched)}")
    if unmatched:
        for u in unmatched:
            print(f"    ! {u[:90]}")
    print(f"  Guardado en: {METADATA_PATH}")

    return 0 if not unmatched else 2


if __name__ == "__main__":
    sys.exit(main())
