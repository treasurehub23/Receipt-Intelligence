import re
import dateparser
from dataclasses import dataclass
from datetime import date, datetime, timedelta

MONTHS = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*"
SEP = r"[-/.]"


DATE_PATTERNS: list[re.Pattern] = [
    re.compile(rf"\b\d{{4}}{SEP}\d{{1,2}}{SEP}\d{{1,2}}\b"),              # 2026-03-14
    re.compile(rf"\b\d{{1,2}}{SEP}\d{{1,2}}{SEP}\d{{4}}\b"),               # 14/03/2026
    re.compile(rf"\b\d{{1,2}}{SEP}\d{{1,2}}{SEP}\d{{2}}\b"),               # 14/03/26
    re.compile(rf"\b\d{{1,2}}[\s-]+{MONTHS}[\s,.-]+\d{{2,4}}\b", re.I),    # 14 Mar 2026
    re.compile(rf"\b{MONTHS}\.?\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+\d{{2,4}}\b", re.I),  # Mar 14, 2026
]
DATE_KEYWORD = re.compile(r"\bDATE\b|\bDT\b|\bISSUED\b|\bPURCHASED\b", re.I)

LOOKS_LIKE_TIME = re.compile(r"\b\d{1,2}:\d{2}\b") 
@dataclass
class DateResult:
    value: date | None
    confidence: float
    source_text: str | None = None
    reason: str = ""

def is_date_ambiguous(token:str) -> bool:
    parts = re.split(SEP, token)
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        return False
    if len(parts[0]) == 4:
        return False
    a, b = int(parts[0]), int(parts[1])
    return a <= 12 and b <= 12 and a != b

def _plausible(d: date, today: date) -> bool:
    return date(2000, 1, 1) <= d <= today + timedelta(days=1)
 
 
def find_date(
    text: str,
    date_order: str = "DMY",
    today: date | None = None,
) -> DateResult:
    """date_order: how to read 03/04/2026. "DMY" (most of the world) or "MDY" (US)."""
    today = today or date.today()
    lines = [l for l in text.splitlines() if l.strip()]
    n = len(lines)
    if n == 0:
        return DateResult(None, 0.0, reason="empty text")
 
    best: tuple[float, date, str, str] | None = None  # score, date, token, reason
 
    for i, line in enumerate(lines):
        for pattern in DATE_PATTERNS:
            for m in pattern.finditer(line):
                token = m.group(0)
                # year-first (2026-03-14) is unambiguous; DMY would reject it
                order = "YMD" if re.match(r"\d{4}\D", token) else date_order
                parsed = dateparser.parse(
                    token,
                    settings={
                        "DATE_ORDER": order,
                        "PREFER_DAY_OF_MONTH": "first",
                        "RETURN_AS_TIMEZONE_AWARE": False,
                    },
                )
                if parsed is None:
                    continue
                d = parsed.date() if isinstance(parsed, datetime) else parsed
                if not _plausible(d, today):
                    continue
 
                score = 1.0
                notes = []
                if DATE_KEYWORD.search(line):
                    score += 1.0
                    notes.append("keyword")
                if LOOKS_LIKE_TIME.search(line):
                    score += 0.5  # receipts print date and time together
                    notes.append("time nearby")
                if i < max(3, n // 3) or i > n * 0.6:
                    score += 0.3  # dates cluster near header or footer
                if best is None or score > best[0]:
                    best = (score, d, token, ", ".join(notes) or "pattern match")
 
    if best is None:
        return DateResult(None, 0.0, reason="no plausible date found")
 
    score, d, token, reason = best
    conf = 0.55 + 0.2 * min(score - 1.0, 1.5)  # 0.55 .. 0.85
    if re.search(MONTHS, token, re.I) or re.match(r"\d{4}", token):
        conf += 0.1  # month name / year-first: no day-month ambiguity
    if is_date_ambiguous(token):
        conf -= 0.2
        reason += f", ambiguous day/month (read as {date_order})"
    return DateResult(d, round(max(0.1, min(conf, 0.95)), 2), token, reason)