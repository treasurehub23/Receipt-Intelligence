
"""Lift the merchant name from the top of a receipt.
 
The merchant is almost always in the first few lines, printed in caps or as a
logo. We score each of those lines and pick the best, rejecting lines that are
clearly something else (phone, address, "WELCOME", a date...).
"""
from __future__ import annotations
 
import re
from dataclasses import dataclass
 
TOP_LINES = 8
 
JUNK_WORDS = re.compile(
    r"\b(WELCOME|THANK|RECEIPT|INVOICE|TAX|CASH\s*SALE|CUSTOMER|COPY|"
    r"TEL|PHONE|FAX|EMAIL|WWW|HTTP|GST|VAT|REG|TIN|ORDER|TABLE|CASHIER|"
    r"DATE|TIME|BILL|SERVED|DUPLICATE|TRANSACTION|TERMINAL)\b|@|\.COM\b",
    re.I,
)
ADDRESS_WORDS = re.compile(
    r"\b(STREET|ST\.|ROAD|RD\.?|AVENUE|AVE|LANE|JALAN|TAMAN|BLOCK|FLOOR|"
    r"ESTATE|CLOSE|CRESCENT|WAY|LAGOS|ABUJA|SUITE|PLAZA|MALL)\b",
    re.I,
)
COMPANY_HINT = re.compile(
    r"\b(LTD|LIMITED|PLC|INC|LLC|SDN\.?\s*BHD|BHD|ENTERPRISES?|STORES?|MART|"
    r"SUPERMARKET|RESTAURANT|CAFE|PHARMACY|BAKERY|KITCHEN|HOTEL|SHOP|"
    r"STATIONERY|BOOKSTORE|COMPANY|CO\.)\b",
    re.I,
)
# Words that describe a business but don't name it. A line made ONLY of these
# ("Restaurant", "Pharmacy Ltd") is a subtitle, not the merchant.
GENERIC_WORDS = {
    "RESTAURANT", "CAFE", "PHARMACY", "BAKERY", "KITCHEN", "HOTEL", "SHOP",
    "STORE", "STORES", "SUPERMARKET", "MART", "COMPANY", "LIMITED", "LTD",
    "ENTERPRISES", "ENTERPRISE", "INC", "PLC", "SDN", "BHD",
}
DATE_LIKE = re.compile(r"\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}")
PHONE_LIKE = re.compile(r"\+?\d[\d\s()-]{7,}")
 
 
@dataclass
class MerchantResult:
    name: str | None
    confidence: float
    source_line: str | None = None
    reason: str = ""
 
 
def _clean(line: str) -> str:
    line = re.sub(r"[^\w&'\-\.\s]", " ", line)      # strip OCR symbol noise
    line = re.sub(r"\s+", " ", line).strip(" -._")
    return line
 
 
def _score(line: str, index: int) -> float | None:
    """None = reject. Otherwise higher is better."""
    raw = line.strip()
    if DATE_LIKE.search(raw) or PHONE_LIKE.search(raw) or JUNK_WORDS.search(raw):
        return None
    cleaned = _clean(raw)
    letters = sum(c.isalpha() for c in cleaned)
    if letters < 3 or len(cleaned) > 45:
        return None
    digits = sum(c.isdigit() for c in cleaned)
    if digits > letters // 2:
        return None  # mostly numbers: not a name
    if re.match(r"^\d", cleaned) and ADDRESS_WORDS.search(cleaned):
        return None  # "12 Allen Avenue": a street address, never a merchant
 
    score = 2.0 - 0.3 * index                       # earlier lines win
    alpha_ratio = letters / max(len(cleaned.replace(" ", "")), 1)
    score += alpha_ratio                            # clean text beats garbled text
    if cleaned.isupper():
        score += 0.4                                # shop names are usually caps
    words = re.findall(r"[A-Za-z]+", cleaned.upper())
    if words and all(w in GENERIC_WORDS for w in words):
        score -= 1.5                                # only a business type, no name
    elif COMPANY_HINT.search(cleaned):
        score += 0.8
    if ADDRESS_WORDS.search(cleaned):
        score -= 1.0                                # "12 Allen Avenue" is an address
    if re.match(r"^\d", cleaned):
        score -= 0.8                                # names rarely start with a number
    return score
 
 
def find_merchant(text: str) -> MerchantResult:
    lines = [l for l in text.splitlines() if l.strip()][:TOP_LINES]
    if not lines:
        return MerchantResult(None, 0.0, reason="empty text")
 
    scored = []
    for i, line in enumerate(lines):
        s = _score(line, i)
        if s is not None:
            scored.append((s, i, line))
 
    if not scored:
        return MerchantResult(None, 0.0, reason="no plausible merchant line")
 
    scored.sort(key=lambda t: t[0], reverse=True)
    best_score, best_idx, best_line = scored[0]
    name = _clean(best_line)
 
    conf = 0.35 + 0.15 * best_score
    if len(scored) > 1 and best_score - scored[1][0] < 0.3:
        conf -= 0.1   # runner-up nearly as good -> less sure
    if best_idx == 0:
        conf += 0.1
    has_signal = name.isupper() or bool(COMPANY_HINT.search(best_line))
    if not has_signal:
        conf = min(conf, 0.55)   # no caps, no company word: could be any stray text
    return MerchantResult(name, round(max(0.1, min(conf, 0.9)), 2), best_line.strip(), "top-line scoring")
 
