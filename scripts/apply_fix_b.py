#!/usr/bin/env python3
"""FIX-B: bajar boost de inmueble_codigos en scoring profile codigo-boost de 10x → 2x.

Cita MS oficial:
> "Start conservative: boost in the 1.25-2.0 range; increase only if recency
>  is truly decisive."
> https://learn.microsoft.com/en-us/azure/search/index-add-scoring-profiles

Razón: el boost 10x amplifica los 141 chunks contaminados con RA03 espurio en
inmueble_codigos (extraído del contenido OCR via LLM, no del path). Bajar a 2x
restaura el rango conservador documentado por MS.

Cambio adicional: bajar nombre_archivo y doc_title de 3x a 2x para coherencia.
content se mantiene en 1.0 (baseline).

Output: tests/backups/index_post_fix_b_body.json (body listo para PUT).
NO ejecuta el PUT — eso se hace por separado con az rest.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKUP = ROOT / "tests" / "backups" / "index_pre_fix_b.json"
OUT = ROOT / "tests" / "backups" / "index_post_fix_b_body.json"


def main() -> None:
    idx = json.loads(BACKUP.read_text())

    # Localizar el scoring profile codigo-boost y modificar weights
    found = False
    for sp in idx.get("scoringProfiles", []):
        if sp.get("name") == "codigo-boost":
            found = True
            old = dict(sp["text"]["weights"])
            sp["text"]["weights"] = {
                "inmueble_codigos": 2.0,   # 10.0 → 2.0 (FIX-B principal)
                "doc_title": 2.0,          # 3.0 → 2.0 (coherencia, dentro de rango MS)
                "nombre_archivo": 2.0,     # 3.0 → 2.0 (coherencia)
                "content": 1.0,            # baseline, sin cambio
            }
            print("[FIX-B] Scoring profile codigo-boost weights:")
            for k in ["inmueble_codigos", "doc_title", "nombre_archivo", "content"]:
                print(f"  {k}: {old.get(k, '-')} → {sp['text']['weights'][k]}")
    if not found:
        raise SystemExit("ERROR: scoring profile codigo-boost no encontrado")

    OUT.write_text(json.dumps(idx, ensure_ascii=False, indent=2))
    print(f"\n[OK] body escrito en {OUT}")
    print(f"     - documentCount esperado: sin cambio (no se re-indexa)")
    print(f"     - defaultScoringProfile: {idx.get('defaultScoringProfile')}")


if __name__ == "__main__":
    main()
