#!/usr/bin/env python3
"""Construye el body de roca-copilot v13 a partir del backup de v12.

FIX-A: Restaurar el default oficial de Foundry para la tool azure_ai_search:
- query_type: "simple" → "vector_semantic_hybrid" (default oficial documentado)
- top_k: 6 → 20 (subir para evitar saturación con un solo doc dominante)

Cita MS oficial:
> "query_type — Defaults to vector_semantic_hybrid. Supported values: simple,
>  vector, semantic, vector_simple_hybrid, vector_semantic_hybrid."
> https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/tools/ai-search

> "Try hybrid queries with semantic ranking. In benchmark testing, this
>  combination consistently produced the most relevant results."
> https://learn.microsoft.com/en-us/azure/search/vector-search-ranking

Preserva: instructions (system prompt v12), kind, model, tool MCP igual.
Solo modifica el sub-objeto azure_ai_search.indexes[0].

Output: tests/backups/agent_v13_body.json (body listo para POST).
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKUP_V12 = ROOT / "tests" / "backups" / "agent_v12_backup.json"
OUT_V13 = ROOT / "tests" / "backups" / "agent_v13_body.json"


def main() -> None:
    v12 = json.loads(BACKUP_V12.read_text())
    defi = v12["definition"]

    # Localizar tool azure_ai_search y modificar
    tools_new = []
    found_search_tool = False
    for tool in defi["tools"]:
        if tool.get("type") == "azure_ai_search":
            found_search_tool = True
            new_tool = json.loads(json.dumps(tool))  # deep copy
            for idx in new_tool["azure_ai_search"]["indexes"]:
                old_qt = idx.get("query_type")
                old_topk = idx.get("top_k")
                idx["query_type"] = "vector_semantic_hybrid"
                idx["top_k"] = 20
                print(f"[FIX-A] index={idx['index_name']}")
                print(f"        query_type: {old_qt} → {idx['query_type']}")
                print(f"        top_k: {old_topk} → {idx['top_k']}")
            tools_new.append(new_tool)
        else:
            tools_new.append(tool)
            print(f"[KEEP] tool type={tool.get('type')} sin cambios")

    if not found_search_tool:
        raise SystemExit("ERROR: no se encontró tool azure_ai_search en v12")

    body = {
        "definition": {
            "instructions": defi["instructions"],
            "kind": defi["kind"],
            "model": defi["model"],
            "tools": tools_new,
        }
    }

    OUT_V13.write_text(json.dumps(body, ensure_ascii=False, indent=2))
    print(f"\n[OK] v13 body escrito en {OUT_V13}")
    print(f"     - instructions length: {len(defi['instructions'])} chars (sin cambios vs v12)")
    print(f"     - model: {defi['model']}")
    print(f"     - tools: {len(tools_new)}")


if __name__ == "__main__":
    main()
