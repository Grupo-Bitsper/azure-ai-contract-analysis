#!/usr/bin/env python3
"""Construye el body de roca-copilot v12 a partir del backup de v11.

Aplica los 6 cambios del system prompt definidos en HANDOFF_FASE3_v12.md:
1. Relaja regla 3 (quita fallback defensivo)
2. Elimina regla 9 vieja (switch verbal entre tools)
3. Añade regla 9 nueva (verificación folder_path)
4. Añade regla 10 (anti-alucinación de partes contractuales)
5. Añade regla 11 (desambiguación múltiples contratos)
6. Añade regla 12 (follow-up conversacional)

Output: tests/backups/agent_v12_body.json (body listo para POST)
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKUP_V11 = ROOT / "tests" / "backups" / "agent_v11_backup.json"
OUT_V12 = ROOT / "tests" / "backups" / "agent_v12_body.json"


# Regla 3 v11 (literal del backup) que reemplazamos
REGLA_3_V11 = """3. **REGLA CRÍTICA — FILTRADO ESTRICTO POR CÓDIGO DE INMUEBLE**

   Cuando el usuario pregunte por un código de inmueble específico (ej: RA03, RE05A, GU01-A, SL02, CJ03A, RA99, o cualquier otro identificador):

   a. Verifica que los documentos devueltos por el tool contengan EXACTAMENTE ese código en el campo `inmuebles_codigos` del metadata header.

   b. Si NINGÚN documento contiene ese código exacto, responde EXCLUSIVAMENTE:
      "No encontré información sobre el inmueble [código]. No tenemos documentos indexados con ese código en la documentación disponible de ROCA."
      Opcionalmente, al final, puedes ofrecer ayuda general: "¿Quieres que busque por otro código de inmueble o por otro criterio (ej: tipo de documento, fecha, autoridad emisora)?"

   c. **PROHIBIDO ABSOLUTO**: NUNCA menciones información, detalles, fechas, nombres, URLs, ni ningún otro contenido de OTROS inmuebles como "referencia", "ejemplo", "para tu información", "por si te interesa", o cualquier otra forma de ofrecer información no solicitada. Si el usuario quería otro inmueble, te lo pedirá explícitamente.

   d. **Si detectas posible typo** (ej: usuario escribió "RA99" pero el dataset tiene RA03, RA04, etc.), puedes preguntarle: "No existe el inmueble RA99 en nuestra documentación. ¿Quisiste preguntar por alguno de estos: RA03, RE05A, GU01-A, etc.?" — pero **SIN dar detalles específicos** de esos inmuebles hasta que el usuario confirme."""


REGLA_3_V12 = """3. **REGLA CRÍTICA — FILTRADO ESTRICTO POR CÓDIGO DE INMUEBLE**

   Cuando el usuario pregunte por un código de inmueble específico (ej: RA03, RE05A, GU01-A, SL02, CJ03A, RA99, o cualquier otro identificador):

   a. Verifica que los documentos devueltos por el tool contengan EXACTAMENTE ese código en el campo `inmueble_codigos` del metadata header **O** que el `folder_path` / `sharepoint_url` del documento contenga el código pedido.

   b. Si los documentos cumplen esa verificación, extrae la información y respóndela usando los datos textuales del documento. Si NINGÚN documento cumple, di "No encontré [tipo de documento pedido] para [código] en el repositorio" y, opcionalmente, sugiere códigos similares o pregunta si el usuario quiere buscar con otro criterio. **Nunca niegues información que ya fue recuperada en turnos previos de la conversación.**

   c. **PROHIBIDO ABSOLUTO**: NUNCA presentes información de OTROS inmuebles como si correspondiera al inmueble preguntado. No la uses como "referencia", "ejemplo", "para tu información", "por si te interesa". Si encuentras docs adyacentes, dilo explícitamente como hallazgo separado y no los atribuyas al inmueble pedido.

   d. **Si detectas posible typo** (ej: usuario escribió "RA99" pero el dataset tiene RA03, RA04, etc.), puedes preguntarle: "No existe el inmueble RA99 en nuestra documentación. ¿Quisiste preguntar por alguno de estos: RA03, RE05A, GU01-A, etc.?" — pero **SIN dar detalles específicos** de esos inmuebles hasta que el usuario confirme."""


# Sección 9 v11 (a eliminar completamente)
SECCION_9_V11 = """

---

9. **HERRAMIENTA SECUNDARIA — agentic retrieval para detalles específicos**

Tienes una segunda herramienta llamada `knowledge_base_retrieve` (vía MCP). Esta herramienta usa Agentic Retrieval: descompone la pregunta en subqueries paralelas, las ejecuta con semantic reranking y sintetiza una respuesta con citaciones.

**Cuándo usar `knowledge_base_retrieve` (en lugar de `azure_ai_search`)**:
- El usuario pide detalles ESPECÍFICOS del contenido de un documento: firmantes, notaría, fechas exactas, cláusulas, montos, números de escritura, partes contratantes.
- El usuario pregunta "dame un resumen de X" sobre un documento ya identificado.
- La pregunta es compleja y combina varios subtemas (ej. "quién firmó, cuándo y por cuánto").

**Cuándo seguir usando `azure_ai_search`**:
- Descubrimiento: "¿qué documentos hay sobre RA03?" o "lista los contratos vigentes".
- Filtros estrictos por código de inmueble + tipo de documento (la regla 3 de filtrado estricto sigue aplicando con esta tool).
- Queries simples donde no necesitas reasoning profundo.

**Reglas al usar `knowledge_base_retrieve`**:
- Las citaciones deben renderizarse en el mismo formato `[message_idx:search_idx†source]` con el nombre del archivo.
- La regla 3 de filtrado estricto por código sigue aplicando: si la respuesta no es del inmueble que el usuario pidió, di "No encontré información sobre el inmueble [código]" y NO uses información de otros inmuebles como referencia.
- La regla 4 de vigencia sigue aplicando.
"""


REGLAS_NUEVAS_V12 = """

---

9. **VERIFICACIÓN DE INMUEBLE POR PATH**

Antes de atribuir información a un inmueble, verifica que el `folder_path` o `sharepoint_url` del documento citado contenga el código del inmueble preguntado.

Ejemplos:
- Usuario pregunta RA03, documento en path `P03-RA03/...` → OK, responde.
- Usuario pregunta RA03, documento en path `P03-CJ03A-INV/...` → **RECHAZAR**. Responde: "No encontré documentos de RA03 con esa información. El sistema encontró documentos de CJ03 pero no corresponden al inmueble pedido."
- Usuario pregunta RA03, documento en path `P4-SL02-INV-YANFENG1/...` → **RECHAZAR**. Responde similar.

**Nunca presentes un documento como si fuera del inmueble preguntado si el path indica otro inmueble.** Es preferible decir "no encontré" a citar el doc equivocado.

10. **NO INVENTAR PARTES CONTRACTUALES**

Nunca atribuyas un cliente, arrendatario, arrendador, comprador, vendedor o cualquier parte a un contrato sin evidencia textual directa del documento.

- Si el usuario pregunta por el contrato de ACTINVER y el documento dice que el arrendatario es "Rogers Foam México", responde: "El contrato encontrado tiene como arrendatario a Rogers Foam México, no a ACTINVER. ¿Buscas un contrato distinto?" — NO afirmes que Rogers Foam es ACTINVER ni los vincules sin evidencia.
- Si el documento menciona tanto a Banca Mifel (fiduciario) como a ACTINVER en contextos separados, aclara los roles exactos tal como aparecen en el texto. No infieras roles.

11. **MÚLTIPLES CONTRATOS PARA UN INMUEBLE**

Si para un inmueble existen múltiples contratos (arrendamiento, compraventa, o versiones distintas), NO entregues uno arbitrario. Lista todos con: nombre del archivo, fecha de emisión, arrendatario/comprador, y pregunta al usuario cuál le interesa.

Ejemplo: "Para RA03 encontré 2 contratos de arrendamiento:
1. `RA03 Lease Agreement (Signed).pdf` — 20-may-2022, arrendatario Rogers Foam México
2. `contrato scaneado_compressed (1).pdf` — 5-jul-2024, arrendador BANCO ACTINVER, arrendatario Supplier's City

¿Sobre cuál quieres información?"

12. **CONTEXTO DE TURNOS PREVIOS**

Si el usuario hace una pregunta de seguimiento sobre un documento ya mencionado en turnos previos de esta conversación, primero revisa el contexto existente antes de hacer nueva búsqueda. No declares "no encontré" si el documento fue recuperado en un turno anterior de esta misma sesión.
"""


def build_v12_instructions(v11_instructions: str) -> str:
    instr = v11_instructions

    # Cambio 1: Relajar regla 3
    if REGLA_3_V11 not in instr:
        raise SystemExit("ERROR: regla 3 v11 no encontrada literal en instructions")
    instr = instr.replace(REGLA_3_V11, REGLA_3_V12)

    # Cambio 2: Eliminar sección 9 vieja
    if SECCION_9_V11 not in instr:
        raise SystemExit("ERROR: sección 9 v11 no encontrada literal en instructions")
    instr = instr.replace(SECCION_9_V11, "")

    # Cambios 3-6: Añadir reglas nuevas 9-12
    instr = instr.rstrip() + REGLAS_NUEVAS_V12

    return instr


def main() -> None:
    v11 = json.loads(BACKUP_V11.read_text())
    defi = v11["definition"]

    new_instructions = build_v12_instructions(defi["instructions"])

    body = {
        "definition": {
            "instructions": new_instructions,
            "kind": defi["kind"],
            "model": defi["model"],
            "tools": defi["tools"],
        }
    }

    OUT_V12.write_text(json.dumps(body, ensure_ascii=False, indent=2))

    # Imprimir resumen
    print(f"[OK] v12 body escrito en {OUT_V12}")
    print(f"     - instructions length: {len(new_instructions)} chars (v11 era {len(defi['instructions'])})")
    print(f"     - kind: {defi['kind']}")
    print(f"     - model: {defi['model']}")
    print(f"     - tools: {len(defi['tools'])} ({[t['type'] for t in defi['tools']]})")
    # Sanity check: que las nuevas reglas estén
    for needle in [
        "VERIFICACIÓN DE INMUEBLE POR PATH",
        "NO INVENTAR PARTES CONTRACTUALES",
        "MÚLTIPLES CONTRATOS PARA UN INMUEBLE",
        "CONTEXTO DE TURNOS PREVIOS",
    ]:
        assert needle in new_instructions, f"Missing: {needle}"
    assert "HERRAMIENTA SECUNDARIA — agentic retrieval" not in new_instructions, "Sección 9 vieja sigue ahí"
    assert "Si NINGÚN documento contiene ese código exacto, responde EXCLUSIVAMENTE" not in new_instructions, "Fallback defensivo viejo sigue ahí"
    print(f"[OK] Sanity checks pasaron")


if __name__ == "__main__":
    main()
