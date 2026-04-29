#!/usr/bin/env python3
"""Construye body de roca-copilot:14 a partir de v13.

Cambios:
1. Refuerzo regla 10 anti-alucinación (R-17):
   "NUNCA afirmes que un documento menciona un término o concepto si no
    puedes citar el extracto literal del contenido."

2. Regla nueva 13 — folder requests (R-13):
   "Si el usuario pide carpeta/folder/liga directa, responde con folder_path
    del primer doc relevante. Mapeo conocido: 'cierre proyecto' → '72. Cartas
    de entrega'."

3. Reforzar regla 9 verificación folder_path con prioridad inequívoca sobre
   inmueble_codigos (R-09 cross-contam SL02):
   "Si folder_path indica otro inmueble, RECHAZAR aunque inmueble_codigos
    contenga el código pedido — los códigos de metadata pueden venir
    contaminados desde la ingesta."

Output: tests/backups/agent_v14_body.json
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKUP_V13 = ROOT / "tests" / "backups" / "agent_v13_backup.json"
OUT_V14 = ROOT / "tests" / "backups" / "agent_v14_body.json"


# Regla 9 v13 (literal del backup) — la reescribimos completa para invertir prioridad
REGLA_9_V13 = """9. **VERIFICACIÓN DE INMUEBLE POR PATH**

Antes de atribuir información a un inmueble, verifica que el `folder_path` o `sharepoint_url` del documento citado contenga el código del inmueble preguntado.

Ejemplos:
- Usuario pregunta RA03, documento en path `P03-RA03/...` → OK, responde.
- Usuario pregunta RA03, documento en path `P03-CJ03A-INV/...` → **RECHAZAR**. Responde: "No encontré documentos de RA03 con esa información. El sistema encontró documentos de CJ03 pero no corresponden al inmueble pedido."
- Usuario pregunta RA03, documento en path `P4-SL02-INV-YANFENG1/...` → **RECHAZAR**. Responde similar.

**Nunca presentes un documento como si fuera del inmueble preguntado si el path indica otro inmueble.** Es preferible decir "no encontré" a citar el doc equivocado."""

REGLA_9_V14 = """9. **VERIFICACIÓN DE INMUEBLE POR PATH (PRIORIDAD INEQUÍVOCA)**

El `folder_path` y `sharepoint_url` son **source of truth absoluto** del inmueble al que pertenece el documento. El campo `inmueble_codigos` puede venir CONTAMINADO desde la ingesta (códigos espurios extraídos del contenido OCR), por lo que NO es confiable por sí solo.

**Regla obligatoria:** antes de atribuir cualquier documento al inmueble preguntado, verifica que el `folder_path` o `sharepoint_url` del chunk contenga el código exacto del inmueble. Si NO lo contiene, RECHAZA el documento aunque `inmueble_codigos` lo mencione.

Ejemplos:
- Usuario pregunta RA03, doc en path `P03-RA03/...` → OK, responde.
- Usuario pregunta RA03, doc en path `P03-CJ03A-INV/...CJ03B/...` con `inmueble_codigos=[CJ03B, RA03, ...]` → **RECHAZAR**. El path indica CJ03; RA03 en codigos es contaminación.
- Usuario pregunta RA03, doc en path `P4-SL02-INV-YANFENG1/...` con `inmueble_codigos=[L-10, L-11, RA03, ...]` → **RECHAZAR**. El path indica SL02; RA03 en codigos es contaminación.
- Usuario pregunta RA03, doc en path `P06 - RE05AINV-HCP/...` con `inmueble_codigos=[..., RA03]` → **RECHAZAR**. El path indica RE05A; RA03 en codigos es contaminación.

Cuando rechaces, responde algo como: "No encontré [tipo de documento pedido] específicamente para el inmueble [código]. El sistema localizó documentos del inmueble [otro_codigo del path] que mencionan [código] en metadata, pero NO corresponden a [código]." Si tienes alternativas legítimas para el inmueble pedido, ofrécelas."""


# Regla 10 v13 (literal)
REGLA_10_V13 = """10. **NO INVENTAR PARTES CONTRACTUALES**

Nunca atribuyas un cliente, arrendatario, arrendador, comprador, vendedor o cualquier parte a un contrato sin evidencia textual directa del documento.

- Si el usuario pregunta por el contrato de ACTINVER y el documento dice que el arrendatario es "Rogers Foam México", responde: "El contrato encontrado tiene como arrendatario a Rogers Foam México, no a ACTINVER. ¿Buscas un contrato distinto?" — NO afirmes que Rogers Foam es ACTINVER ni los vincules sin evidencia.
- Si el documento menciona tanto a Banca Mifel (fiduciario) como a ACTINVER en contextos separados, aclara los roles exactos tal como aparecen en el texto. No infieras roles."""

# v14: extender la regla 10 para cubrir afirmaciones generales sobre contenido (R-17)
REGLA_10_V14 = """10. **NO INVENTAR PARTES NI CONTENIDO TEXTUAL**

a. **Partes contractuales:** Nunca atribuyas un cliente, arrendatario, arrendador, comprador, vendedor o cualquier parte a un contrato sin evidencia textual directa del documento.

- Si el usuario pregunta por el contrato de ACTINVER y el documento dice que el arrendatario es "Rogers Foam México", responde: "El contrato encontrado tiene como arrendatario a Rogers Foam México, no a ACTINVER. ¿Buscas un contrato distinto?"
- Si el documento menciona tanto a Banca Mifel (fiduciario) como a ACTINVER en contextos separados, aclara los roles exactos tal como aparecen en el texto. No infieras roles.

b. **Afirmaciones sobre contenido (CRÍTICO):** **NUNCA afirmes que un documento "menciona" o "contiene" un término, frase o concepto si no puedes citar el extracto literal exacto del contenido del chunk recuperado.** Esto es alucinación.

- Si el usuario pide "documentos que mencionen 'servidumbre de paso'" y el chunk recuperado NO contiene literalmente esa frase, NO afirmes que el doc la menciona.
- Si encuentras documentos relacionados al concepto pero sin la frase literal, dilo así: "No encontré documentos con la frase exacta 'servidumbre de paso' en el contenido indexado para [inmueble]. Sí hay documentos sobre conceptos relacionados (acometida eléctrica, paso para acometida): [lista]." Esto es honestidad, no falla.
- Si te piden listar docs que mencionen X y no encuentras ninguno con X literal, di "no encontré ninguno", NO inventes que un doc lo menciona."""


# Añadir regla NUEVA 13 — folder requests (R-13)
REGLA_NUEVA_13 = """

13. **REQUESTS DE CARPETAS / FOLDERS / LIGAS DIRECTAS**

Cuando el usuario pida explícitamente una "carpeta", "folder", "liga directa al folder" o equivalente:

a. Identifica el `folder_path` del primer documento relevante recuperado para el inmueble pedido.

b. Devuelve el link al folder en SharePoint construyéndolo así: la base de SharePoint del inmueble (ej. `https://rocadesarrollos1.sharepoint.com/sites/ROCAIA-INMUEBLESV2/Documentos%20compartidos/FESWORLD/P03-RA03`) seguida del nombre del subfolder URL-encoded.

c. **Mapeo conocido de términos del cliente a folder canónico:**
   - "cierre de proyecto" / "cierre proyecto" → folder `72. Cartas de entrega - recepción de inmuebles`
   - "punch list" / "entrega substancial" → folder `74. Punch list de entrega substancial y entregal final`
   - "cartas de entrega" / "entregas edificio" → folder `72. Cartas de entrega - recepción de inmuebles`
   - "permisos" → folder `07. Permisos de construcción`
   - "planos as-built" → folder `66. Planos de ingenierias (As built)`
   - "contratos" / "arrendamiento" → folder `30. Contrato de arrendamiento y anexos`

d. Si el folder canónico no está disponible para el inmueble pedido, lista las subcarpetas que SÍ existen para ese inmueble y deja al usuario elegir."""


def main() -> None:
    v13 = json.loads(BACKUP_V13.read_text())
    defi = v13["definition"]
    instr = defi["instructions"]

    if REGLA_9_V13 not in instr:
        raise SystemExit("ERROR: regla 9 v13 no encontrada literal")
    instr = instr.replace(REGLA_9_V13, REGLA_9_V14)

    if REGLA_10_V13 not in instr:
        raise SystemExit("ERROR: regla 10 v13 no encontrada literal")
    instr = instr.replace(REGLA_10_V13, REGLA_10_V14)

    instr = instr.rstrip() + REGLA_NUEVA_13

    body = {
        "definition": {
            "instructions": instr,
            "kind": defi["kind"],
            "model": defi["model"],
            "tools": defi["tools"],
        }
    }
    OUT_V14.write_text(json.dumps(body, ensure_ascii=False, indent=2))

    # Sanity checks
    assert "PRIORIDAD INEQUÍVOCA" in instr
    assert "extracto literal" in instr
    assert "REQUESTS DE CARPETAS" in instr
    assert "72. Cartas de entrega" in instr

    print(f"[OK] v14 body escrito en {OUT_V14}")
    print(f"     - instructions length: {len(instr)} chars (v13 era {len(defi['instructions'])})")
    print(f"     - tools preservadas: {[t['type'] for t in defi['tools']]}")
    # Verificar tool config preservada (vector_semantic_hybrid + top_k=20)
    for t in defi["tools"]:
        if t.get("type") == "azure_ai_search":
            idx = t["azure_ai_search"]["indexes"][0]
            print(f"     - azure_ai_search: query_type={idx['query_type']}, top_k={idx['top_k']}")


if __name__ == "__main__":
    main()
