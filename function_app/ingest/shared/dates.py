"""Date handling ported 1:1 from scripts/ingestion/ingest_prod.py.

Includes the F4B post-smoke fixes that resolved the vigencia bug:
- _normalize_date rejects malformed placeholders (2021-__-__, 2021-XX-XX)
- _compute_end_from_duration calculates fin_iso from duracion_texto when
  the discovery output didn't include it explicitly.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone


def normalize_date(s: str | None) -> str | None:
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    if "_" in s or "?" in s:
        return None
    if re.search(r"\dX|X\d|XX", s.upper()):
        return None
    try:
        dt_str = s
        if "T" not in dt_str:
            dt_str = dt_str + "T00:00:00"
        if not dt_str.endswith("Z") and "+" not in dt_str[10:]:
            dt_str = dt_str + "Z"
        datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt_str
    except Exception:
        return None


def compute_end_from_duration(start_iso: str | None, duracion_texto: str | None) -> str | None:
    if not start_iso or not duracion_texto:
        return None
    try:
        start = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
    except Exception:
        return None

    text = duracion_texto.lower().strip()
    word_to_num = {
        "uno": "1", "un": "1", "una": "1",
        "dos": "2", "tres": "3", "cuatro": "4", "cinco": "5",
        "seis": "6", "siete": "7", "ocho": "8", "nueve": "9", "diez": "10",
        "doce": "12", "dieciocho": "18", "veinte": "20", "treinta": "30",
        "treinta y seis": "36", "cuarenta y ocho": "48", "setenta y dos": "72",
    }
    for word, num in word_to_num.items():
        text = re.sub(rf"\b{word}\b", num, text)

    m = re.search(r"(\d+)\s*(d[ií]as?|mes(?:es)?|a[nñ]os?|semanas?)", text)
    if not m:
        return None
    n = int(m.group(1))
    unit = m.group(2)

    try:
        if unit.startswith("d"):
            end = start + timedelta(days=n)
        elif unit.startswith("mes"):
            month0 = start.month + n
            year = start.year + (month0 - 1) // 12
            month = ((month0 - 1) % 12) + 1
            is_leap = (year % 4 == 0 and year % 100 != 0) or year % 400 == 0
            days_in_month = [31, 29 if is_leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
            day = min(start.day, days_in_month)
            end = start.replace(year=year, month=month, day=day)
        elif unit.startswith("a"):
            is_leap = (start.year + n) % 4 == 0 and ((start.year + n) % 100 != 0 or (start.year + n) % 400 == 0)
            day = start.day
            if start.month == 2 and start.day == 29 and not is_leap:
                day = 28
            end = start.replace(year=start.year + n, day=day)
        elif unit.startswith("sem"):
            end = start + timedelta(weeks=n)
        else:
            return None
    except Exception:
        return None

    return end.strftime("%Y-%m-%dT%H:%M:%SZ")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
