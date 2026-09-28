
/
















































Items · PY
"""Best-effort line items. Partial output is fine: this never blocks the milestone."""
from __future__ import annotations
 
import re
from decimal import Decimal
 
from pydantic import BaseModel
 
from .money import SUBTOTAL, TOTAL_KEYS, _normalize, extract_amounts, is_summary_line
 
 
class LineItem(BaseModel):
    description: str
    quantity: int = 1
    price: Decimal          # price as printed on the line (line total)
 
 
# "2 x Rice 3,000.00" | "2 Rice 3000" | "Rice 1500.00" | "Rice  2 @ 750  1500"
QTY_PREFIX = re.compile(r"^\s*(\d{1,3})\s*[xX*]?\s+(?=[A-Za-z])")
TRAILING_QTY = re.compile(r"\s+\d{1,3}\s*[xX@]\s*[\d.,]+\s*$")
DATE_LIKE = re.compile(r"\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}")
PHONE_LIKE = re.compile(r"\+?\d[\d\s()-]{8,}")
PRICE_AT_END = re.compile(r"(?<=\s)[\d.,]*\d\s*$")
 
 
def _body_lines(lines: list[str]) -> list[str]:
    """Only look above the first subtotal/total line."""
    for i, line in enumerate(lines):
        u = _normalize(line)
        if SUBTOTAL.search(u) or any(p.search(u) for p, w in TOTAL_KEYS if w >= 2.0):
            return lines[:i]
    return lines
 
 
def find_line_items(text: str) -> list[LineItem]:
    lines = [l for l in text.splitlines() if l.strip()]
    items: list[LineItem] = []
 
    for line in _body_lines(lines):
        if is_summary_line(line) or DATE_LIKE.search(line) or PHONE_LIKE.search(line):
            continue
        stripped = line.strip()
        m = PRICE_AT_END.search(stripped)
        if not m:
            continue                          # a price must END the line
        amounts = extract_amounts(m.group(0))
        if not amounts:
            continue
        price = amounts[-1]
 
        # description = everything before the final amount, minus qty noise
        desc = stripped[: m.start()]
        desc = TRAILING_QTY.sub("", desc)
        qty = 1
        q = QTY_PREFIX.match(desc)
        if q:
            qty = int(q.group(1))
            desc = desc[q.end():]
        desc = re.sub(r"[^\w&'()/\-\.\s]", " ", desc)
        desc = re.sub(r"\s+", " ", desc).strip(" -._")
 
        letters = sum(c.isalpha() for c in desc)
        if letters < 3 or letters < len(desc) // 2:
            continue                          # not a real description
        if price <= 0:
            continue
        items.append(LineItem(description=desc, quantity=qty, price=price))
    return items
 
