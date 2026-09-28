
from __future__ import annotations
"""Extract the total and currency from raw OCR text.

Approach: don't hunt for "the" total with one regex. Instead
  1. collect every amount on every line,
  2. score each candidate (keyword strength, position, sanity checks),
  3. pick the best and report how confident we are.
"""

import re
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

# ---------------------------------------------------------------- amounts
# Matches 1,234.50 | 1.234,50 | 12.50 | 12,50 | 1500  (not inside longer numbers)
AMOUNT_RE = re.compile(
    r"(?<![\w.,])"
    r"(\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)"
    r"(?![\d%])"
)
# OCR often splits decimals: "12 .50" / "12. 50" -> "12.50"
SPLIT_DECIMAL_RE = re.compile(r"(?<=\d)\s*([.,])\s*(?=\d{2}\b)")


def to_decimal(token: str) -> Decimal | None:
    """Turn '1,234.50' / '1.234,50' / '12,50' / '1,234' into a Decimal."""
    has_dot, has_com = "." in token, "," in token
    if has_dot and has_com:
        # whichever separator comes last is the decimal point
        dec = "." if token.rfind(".") > token.rfind(",") else ","
        thou = "," if dec == "." else "."
        token = token.replace(thou, "").replace(dec, ".")
    elif has_dot or has_com:
        sep = "." if has_dot else ","
        head, _, tail = token.rpartition(sep)
        if token.count(sep) > 1 or len(tail) == 3:
            token = token.replace(sep, "")  # thousands separator
        else:
            token = f"{head}.{tail}"  # decimal separator
    try:
        return Decimal(token)
    except InvalidOperation:
        return None


def extract_amounts(line: str) -> list[Decimal]:
    line = SPLIT_DECIMAL_RE.sub(r"\1", line)
    out = []
    for m in AMOUNT_RE.finditer(line):
        value = to_decimal(m.group(1))
        if value is not None:
            out.append(value)
    return out


# ---------------------------------------------------------------- total
def _normalize(line: str) -> str:
    u = line.upper()
    u = re.sub(r"T[O0]TA[L1I|]", "TOTAL", u)  # T0TAL, TOTA1, TOTAI ...
    return u


SUBTOTAL = re.compile(r"SUB\s*-?\s*TOTAL|SUB\s*TTL")
HARD_BAD = re.compile(
    r"CHANGE|CASH|TENDER|TIP\b|GRATUITY|DISCOUNT|SAVING|ROUNDING|"
    r"QTY|ITEMS?\b|POINTS|CARD\s*NO|VISA|MASTERCARD"
)
TAX = re.compile(r"\bTAX\b|\bVAT\b|\bGST\b|\bSST\b")
TOTAL_KEYS: list[tuple[re.Pattern, float]] = [
    (re.compile(r"GRAND\s*TOTAL"), 3.0),
    (re.compile(r"(TOTAL|AMOUNT|AMT|BALANCE)\s*(DUE|PAYABLE)|AMOUNT\s*TO\s*PAY"), 3.0),
    (re.compile(r"NET\s*TOTAL|TOTAL\s*AMOUNT|TOTAL\s*SALES?"), 2.5),
    (re.compile(r"\bTOTAL\b"), 2.0),
    (re.compile(r"\bPAYABLE\b|\bTO\s*PAY\b"), 1.5),
]


def _line_score(line: str) -> float | None:
    """None = this line must NOT supply the total. 0 = no keyword."""
    u = _normalize(line)
    if SUBTOTAL.search(u) or HARD_BAD.search(u):
        return None
    # "TOTAL (INCL. GST)" is a real total; a bare "GST 6%" line is not
    if TAX.search(u) and not re.search(r"INCL|INC\.", u):
        return None
    for pattern, weight in TOTAL_KEYS:
        if pattern.search(u):
            return weight
    return 0.0


@dataclass
class TotalResult:
    amount: Decimal | None
    confidence: float
    source_line: str | None = None
    reason: str = ""


def find_total(text: str) -> TotalResult:
    lines = [l for l in text.splitlines() if l.strip()]
    n = len(lines)
    if n == 0:
        return TotalResult(None, 0.0, reason="empty text")

    candidates: list[tuple[float, Decimal, str]] = []  # (score, amount, line)
    fallback: list[tuple[Decimal, str]] = []
    subtotal: Decimal | None = None

    for i, line in enumerate(lines):
        if SUBTOTAL.search(_normalize(line)):
            amts = extract_amounts(line) or (
                extract_amounts(lines[i + 1]) if i + 1 < n else []
            )
            if amts:
                subtotal = amts[-1]

        score = _line_score(line)
        if score is None:
            continue
        position_bonus = 0.5 * (i / n)  # totals live near the bottom
        amts = extract_amounts(line)

        if score > 0:
            if amts:
                candidates.append((score + position_bonus, amts[-1], line))
            elif i + 1 < n:
                # OCR often puts the number on the NEXT line
                nxt = extract_amounts(lines[i + 1])
                if nxt and _line_score(lines[i + 1]) is not None:
                    candidates.append((score * 0.8 + position_bonus, nxt[-1], line))
        elif amts and i >= n // 2:
            fallback.append((max(amts), line))

    if candidates:
        candidates.sort(key=lambda c: (c[0], c[1]), reverse=True)
        score, amount, line = candidates[0]
        conf = 0.9 if score >= 3 else 0.8 if score >= 2 else 0.65
        reason = "keyword match"
        # same amount seen on several keyword lines -> more trust
        if sum(1 for c in candidates if c[1] == amount) > 1:
            conf = min(conf + 0.05, 0.98)
            reason += ", repeated"
        # sanity: total should not be smaller than the subtotal
        if subtotal is not None and amount < subtotal:
            conf = max(conf - 0.3, 0.2)
            reason += ", smaller than subtotal (suspicious)"
        return TotalResult(amount, round(conf, 2), line.strip(), reason)

    if fallback:
        amount, line = max(fallback, key=lambda f: f[0])
        return TotalResult(amount, 0.35, line.strip(), "no keyword; largest amount in lower half")

    return TotalResult(None, 0.0, reason="no amounts found")


# ---------------------------------------------------------------- currency
SYMBOLS = {"₦": "NGN", "$": "USD", "£": "GBP", "€": "EUR", "₹": "INR", "¥": "JPY"}
CODES = ("NGN", "USD", "GBP", "EUR", "INR", "MYR", "CAD", "AUD", "ZAR", "GHS", "KES", "JPY", "CNY")
CODE_RE = re.compile(r"\b(" + "|".join(CODES) + r")\b", re.I)
RM_RE = re.compile(r"\bRM\s?\d", re.I)  # Malaysian ringgit (SROIE is full of these)
# Tesseract often misreads the naira sign as N or #
NAIRA_MISREAD_RE = re.compile(r"(?<![A-Za-z])[N#]\s?\d{1,3}(?:,\d{3})*(?:\.\d{2})")


@dataclass
class CurrencyResult:
    code: str
    confidence: float
    source: str  # "symbol" | "code" | "default"


def find_currency(text: str, default: str = "USD") -> CurrencyResult:
    raw_votes: defaultdict[str, float] = defaultdict(float)
    for sym, sym_code in SYMBOLS.items():
        raw_votes[sym_code] += text.count(sym)
    for m in CODE_RE.finditer(text):
        raw_votes[m.group(1).upper()] += 2.0  # explicit codes are stronger evidence
    raw_votes["MYR"] += 2.0 * len(RM_RE.findall(text))
    if default == "NGN":
        raw_votes["NGN"] += 0.5 * len(NAIRA_MISREAD_RE.findall(text))

    votes = {c: v for c, v in raw_votes.items() if v > 0}  # drop zero counts
    if not votes:
        return CurrencyResult(default, 0.3, "default")

    code = max(votes, key=lambda c: votes[c])
    count = votes[code]
    share = count / sum(votes.values())
    conf = round(min(0.95, 0.6 + 0.35 * share), 2)
    if code == "USD" and "$" in text and not CODE_RE.search(text):
        conf = min(conf, 0.7)  # "$" is shared by USD/CAD/AUD/...
    source = "code" if CODE_RE.search(text) or RM_RE.search(text) else "symbol"
    return CurrencyResult(code, conf, source)


# ---------------------------------------------------------------- one call
def extract_info(text: str, default_currency: str = "USD") -> dict:
    total = find_total(text)
    cur = find_currency(text, default_currency)
    return {
        "total": total.amount,
        "total_conf": total.confidence,
        "total_line": total.source_line,
        "currency": cur.code,
        "currency_conf": cur.confidence,
    }

def parse_receipt(ocr_result):
    if ocr_result["source"] == "easyocr":
        raw_text = "\n".join(item["text"] for item in ocr_result["text"])
    else:
        raw_text = ocr_result["text"]
    money = extract_info(raw_text)
    return {
        "raw_text": raw_text,
        "total": money["total"],
        "total_conf": money["total_conf"],
        "total_line": money["total_line"],
        "currency": money["currency"],
        "currency_conf": money["currency_conf"],
    }