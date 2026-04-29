#!/usr/bin/env python3
"""Golden set runner para ROCA Copilot.

Corre los 16 casos de tests/golden_set_roca.jsonl contra el agente live en
Foundry (version activa según version_selector) y guarda respuestas +
veredicto automático.

Uso:
    python scripts/run_golden_set.py                       # raw, sin middleware
    python scripts/run_golden_set.py --middleware          # con pre-search
    python scripts/run_golden_set.py --only R-04,R-07      # subset
    python scripts/run_golden_set.py --label fase1_patch   # tag para archivo salida
    python scripts/run_golden_set.py --dry-run             # imprime prompts sin llamar

Requisitos:
    az login previo (DefaultAzureCredential lo toma)
    pip install azure-identity requests
    Para --middleware además: pip install azure-search-documents
    y env vars SEARCH_ENDPOINT (+ SEARCH_INDEX opcional, default roca-contracts-v1)

Output:
    tests/results/<label>_<YYYY-MM-DD_HHMM>.jsonl    un caso por línea
    tests/results/<label>_<YYYY-MM-DD_HHMM>.md       reporte leíble
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from azure.identity import DefaultAzureCredential


ROOT = Path(__file__).resolve().parent.parent
GOLDEN_SET = ROOT / "tests" / "golden_set_roca.jsonl"
RESULTS_DIR = ROOT / "tests" / "results"

RESPONSES_ENDPOINT = (
    "https://rocadesarrollo-resource.services.ai.azure.com"
    "/api/projects/rocadesarrollo/openai/v1/responses"
)
AGENT_NAME = "roca-copilot"
TOKEN_SCOPE = "https://ai.azure.com/.default"
REQUEST_TIMEOUT = 90
SLEEP_BETWEEN_CASES = 15
MAX_429_RETRIES = 4

KNOWN_CODES = {
    "RA03", "GU01A", "GU01-TEN", "CJ03", "CJ03B",
    "RE05", "RE05A", "SL02", "SHELL-SLP02",
}
CODE_PATTERN = re.compile(
    r"\b[A-Z]{2,5}(?:-?[A-Z0-9]{1,5})?\d{2,3}[A-Z]?(?:-[A-Z0-9]{1,8})?\b",
    re.IGNORECASE,
)


def extract_codes(text: str) -> list[str]:
    text_upper = text.upper()
    found: list[str] = []
    for code in KNOWN_CODES:
        variations = {code, code.replace("-", " "), code.replace("-", "")}
        for v in variations:
            if re.search(rf"\b{re.escape(v)}\b", text_upper):
                if code not in found:
                    found.append(code)
                break
    if not found:
        for m in CODE_PATTERN.findall(text_upper):
            if m not in found:
                found.append(m)
    return found


def pre_search(user_text: str, codes: list[str], top: int = 5) -> str:
    try:
        from azure.search.documents import SearchClient
    except ImportError:
        print("[WARN] azure-search-documents no instalado — omitiendo pre-search")
        return ""

    endpoint = os.environ.get("SEARCH_ENDPOINT")
    if not endpoint:
        print("[WARN] SEARCH_ENDPOINT no seteado — omitiendo pre-search")
        return ""
    index_name = os.environ.get("SEARCH_INDEX", "roca-contracts-v1")

    client = SearchClient(
        endpoint=endpoint,
        index_name=index_name,
        credential=DefaultAzureCredential(),
    )
    codes_csv = ",".join(codes)
    filter_expr = f"inmueble_codigos/any(c: search.in(c, '{codes_csv}', ','))"
    try:
        results = list(client.search(
            search_text=user_text,
            filter=filter_expr,
            top=top,
            query_type="semantic",
            semantic_configuration_name="default-semantic-config",
            select=[
                "nombre_archivo", "folder_path", "doc_type",
                "inmueble_codigo_principal", "inmueble_codigos", "sharepoint_url",
                "fecha_emision", "fecha_vencimiento", "es_vigente", "content",
            ],
        ))
    except Exception as exc:
        print(f"[WARN] pre-search falló: {exc}")
        return ""
    if not results:
        return ""
    lines = [
        f"[CONTEXTO PRE-FILTRADO POR CÓDIGO(S): {', '.join(codes)}]",
        f"Se encontraron {len(results)} resultados relevantes server-side.",
        "",
    ]
    for i, r in enumerate(results, 1):
        snippet = (r.get("content") or "").replace("\n", " ")[:400]
        lines.extend([
            f"--- Resultado {i} ---",
            f"Archivo: {r.get('nombre_archivo', '?')}",
            f"Folder: {r.get('folder_path', '')}",
            f"Tipo: {r.get('doc_type', '?')}",
            f"Código principal: {r.get('inmueble_codigo_principal', '?')}",
            f"Todos los códigos: {', '.join(r.get('inmueble_codigos') or [])}",
            f"URL: {r.get('sharepoint_url', '')}",
            f"Extracto: {snippet}",
            "",
        ])
    return "\n".join(lines)


def call_agent(user_text: str, token: str, with_middleware: bool) -> dict[str, Any]:
    input_text = user_text
    middleware_applied = False
    if with_middleware:
        codes = extract_codes(user_text)
        if codes:
            ctx = pre_search(user_text, codes)
            if ctx:
                input_text = (
                    f"{user_text}\n\n"
                    "---\n"
                    "El middleware pre-filtró el índice por los códigos detectados "
                    "y encontró estos resultados autoritativos. Basa tu respuesta "
                    "EXCLUSIVAMENTE en estos documentos — si no responden la "
                    "pregunta, dilo y no inventes de otros archivos.\n\n"
                    f"{ctx}"
                )
                middleware_applied = True

    t0 = time.time()
    attempts = 0
    while True:
        attempts += 1
        resp = requests.post(
            RESPONSES_ENDPOINT,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "agent_reference": {"type": "agent_reference", "name": AGENT_NAME},
                "input": input_text,
            },
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code == 429 and attempts <= MAX_429_RETRIES:
            retry_after = int(resp.headers.get("retry-after", "30"))
            wait = max(retry_after, 20 * attempts)
            print(f"    [429] retry {attempts}/{MAX_429_RETRIES}, esperando {wait}s")
            time.sleep(wait)
            continue
        break
    latency_ms = int((time.time() - t0) * 1000)
    resp.raise_for_status()
    data = resp.json()

    answer = ""
    tool_calls: list[str] = []
    for item in data.get("output", []):
        itype = item.get("type")
        if itype == "message":
            for block in item.get("content", []):
                if block.get("type") == "output_text":
                    answer = block.get("text", "").strip()
        elif itype and "tool" in itype.lower():
            tool_calls.append(itype)

    return {
        "answer": answer,
        "latency_ms": latency_ms,
        "tool_calls": tool_calls,
        "middleware_applied": middleware_applied,
        "raw_output_types": [i.get("type") for i in data.get("output", [])],
    }


def auto_verdict(answer: str, case: dict[str, Any]) -> tuple[str, list[str]]:
    """Devuelve (veredicto, razones). Heurística simple con must_contain_any / must_not_contain.

    PASS   todas las must_not_contain ausentes Y al menos una must_contain_any presente
    FAIL   alguna must_not_contain presente
    PARTIAL todas las must_not_contain ausentes pero ninguna must_contain_any presente
    SKIP   caso marcado BLOQUEADO en baseline
    """
    reasons: list[str] = []
    if case.get("baseline_v11_verdict") == "BLOQUEADO":
        return "SKIP", ["caso bloqueado por data gap (R-08)"]

    ans_lower = answer.lower()
    must_not = [s for s in case.get("must_not_contain", []) if s]
    must_any = [s for s in case.get("must_contain_any", []) if s]

    triggered_must_not = [s for s in must_not if s.lower() in ans_lower]
    if triggered_must_not:
        reasons.append(f"dispara must_not_contain: {triggered_must_not}")
        return "FAIL", reasons

    matched_any = [s for s in must_any if s.lower() in ans_lower]
    if must_any and not matched_any:
        reasons.append(f"no matchea ningún must_contain_any: {must_any}")
        return "PARTIAL", reasons

    if matched_any:
        reasons.append(f"matchea: {matched_any}")
    return "PASS", reasons


def load_cases(only: list[str] | None) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    with GOLDEN_SET.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            c = json.loads(line)
            if only and c["case_id"] not in only:
                continue
            cases.append(c)
    return cases


def write_markdown_report(results: list[dict[str, Any]], out_md: Path, label: str, with_middleware: bool) -> None:
    pass_n = sum(1 for r in results if r["verdict"] == "PASS")
    partial_n = sum(1 for r in results if r["verdict"] == "PARTIAL")
    fail_n = sum(1 for r in results if r["verdict"] == "FAIL")
    skip_n = sum(1 for r in results if r["verdict"] == "SKIP")
    error_n = sum(1 for r in results if r["verdict"] == "ERROR")
    total = len(results)
    gradable = total - skip_n - error_n
    score = f"{pass_n}/{gradable}" if gradable else "n/a"

    lines = [
        f"# Golden set run — {label}",
        "",
        f"- Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Middleware pre-search: {'ON' if with_middleware else 'OFF'}",
        f"- Endpoint: `{RESPONSES_ENDPOINT}`",
        f"- Agent: `{AGENT_NAME}` (versión según version_selector)",
        "",
        "## Score",
        "",
        f"| PASS | PARTIAL | FAIL | SKIP | ERROR | Score gradable |",
        f"|---|---|---|---|---|---|",
        f"| {pass_n} | {partial_n} | {fail_n} | {skip_n} | {error_n} | **{score}** |",
        "",
        "## Resultados por caso",
        "",
    ]
    for r in results:
        lines.extend([
            f"### {r['case_id']} — {r['category']} — **{r['verdict']}**",
            "",
            f"**Prompt:** {r['prompt']}",
            "",
            f"**Esperado:** {r['expected_summary']}",
            "",
            f"**Baseline v11 esperado:** `{r.get('baseline_v11_verdict', '?')}`",
            "",
            f"**Verdict automático:** `{r['verdict']}` — {', '.join(r.get('verdict_reasons', []))}",
            "",
            f"**Latencia:** {r.get('latency_ms', 'n/a')}ms | **Tool calls:** {r.get('tool_calls', [])} | **Middleware:** {r.get('middleware_applied', False)}",
            "",
            "**Respuesta del agente:**",
            "",
            "```",
            r.get("answer", "") or "(vacío)",
            "```",
            "",
            "---",
            "",
        ])
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--middleware", action="store_true", help="Activa pre_search_by_codes (replica flujo Teams real)")
    ap.add_argument("--only", default=None, help="Lista comma-separated de case_ids (ej: R-04,R-07)")
    ap.add_argument("--label", default="baseline_v11", help="Tag para nombre de archivo de salida")
    ap.add_argument("--dry-run", action="store_true", help="Imprime prompts sin llamar al agente")
    args = ap.parse_args()

    only = [c.strip() for c in args.only.split(",")] if args.only else None
    cases = load_cases(only)
    print(f"[INFO] {len(cases)} casos cargados" + (f" (filtrados por {only})" if only else ""))

    if args.dry_run:
        for c in cases:
            print(f"\n--- {c['case_id']} ---\n{c['prompt']}\n")
        return 0

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    out_jsonl = RESULTS_DIR / f"{args.label}_{ts}.jsonl"
    out_md = RESULTS_DIR / f"{args.label}_{ts}.md"

    print("[INFO] Obteniendo token Azure AD (DefaultAzureCredential)...")
    cred = DefaultAzureCredential()
    token = cred.get_token(TOKEN_SCOPE).token
    print(f"[INFO] Token OK. Corriendo casos con middleware={args.middleware}")

    results: list[dict[str, Any]] = []
    with out_jsonl.open("w", encoding="utf-8") as fout:
        for idx, case in enumerate(cases, 1):
            print(f"\n[{idx}/{len(cases)}] {case['case_id']} — {case['prompt'][:80]}...")
            entry: dict[str, Any] = {**case}
            try:
                call = call_agent(case["prompt"], token, args.middleware)
                entry.update(call)
                verdict, reasons = auto_verdict(call["answer"], case)
                entry["verdict"] = verdict
                entry["verdict_reasons"] = reasons
                print(f"  -> {verdict} ({call['latency_ms']}ms) | {reasons}")
            except requests.HTTPError as e:
                entry["verdict"] = "ERROR"
                entry["verdict_reasons"] = [f"HTTP {e.response.status_code}: {e.response.text[:200]}"]
                print(f"  -> ERROR HTTP {e.response.status_code}")
            except Exception as e:
                entry["verdict"] = "ERROR"
                entry["verdict_reasons"] = [f"{type(e).__name__}: {e}"]
                print(f"  -> ERROR {type(e).__name__}: {e}")
            results.append(entry)
            fout.write(json.dumps(entry, ensure_ascii=False) + "\n")
            fout.flush()
            if idx < len(cases):
                time.sleep(SLEEP_BETWEEN_CASES)

    write_markdown_report(results, out_md, args.label, args.middleware)
    pass_n = sum(1 for r in results if r["verdict"] == "PASS")
    partial_n = sum(1 for r in results if r["verdict"] == "PARTIAL")
    fail_n = sum(1 for r in results if r["verdict"] == "FAIL")
    skip_n = sum(1 for r in results if r["verdict"] == "SKIP")
    error_n = sum(1 for r in results if r["verdict"] == "ERROR")
    print(f"\n[DONE] PASS={pass_n} PARTIAL={partial_n} FAIL={fail_n} SKIP={skip_n} ERROR={error_n}")
    print(f"[DONE] JSONL: {out_jsonl}")
    print(f"[DONE] Reporte: {out_md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
