#!/usr/bin/env python3
"""Ampliar synonym map roca-synonyms con grupos para R-13 y R-17.

R-13: cliente pregunta por "carpeta de cierre de proyecto" pero docs reales
      están en folder "72. Cartas de entrega" / "74. Punch list" — añadir
      grupo de sinónimos para que el query expanda.

R-17: cliente pregunta por "servidumbre de paso" pero los docs RA03 reales
      hablan de "acometida eléctrica" / "paso para acometida" — añadir grupo.

Output: tests/backups/synonyms_post_expand_body.json (body listo para PUT).
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKUP = ROOT / "tests" / "backups" / "synonyms_pre_expand.json"
OUT = ROOT / "tests" / "backups" / "synonyms_post_expand_body.json"

NEW_GROUPS = [
    # R-13: cierre proyecto = cartas entrega, entregas edificio, punch list, certificado substancial
    "cierre de proyecto, cierre proyecto, cartas de entrega, entregas edificio, entrega recepcion, entrega recepcion inmuebles, punch list, certificado substancial, entrega final",
    # R-17: servidumbre paso = acometida, paso acometida, paso electrico
    "servidumbre de paso, servidumbre paso, acometida, acometida electrica, paso para acometida, paso acometida, distribucion subestacion",
]


def main() -> None:
    sm = json.loads(BACKUP.read_text())
    current = sm.get("synonyms", "")
    new = current + "\n" + "\n".join(NEW_GROUPS)
    sm["synonyms"] = new

    OUT.write_text(json.dumps(sm, ensure_ascii=False, indent=2))
    print(f"[OK] body escrito en {OUT}")
    print(f"     - grupos antes: {len([l for l in current.split(chr(10)) if l.strip()])}")
    print(f"     - grupos después: {len([l for l in new.split(chr(10)) if l.strip()])}")
    print(f"     - grupos nuevos:")
    for g in NEW_GROUPS:
        print(f"       · {g}")


if __name__ == "__main__":
    main()
