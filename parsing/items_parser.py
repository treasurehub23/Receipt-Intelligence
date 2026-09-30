"""Best-effort line items. Partial output is fine: this never blocks the milestone."""
from __future__ import annotations

import re
from decimal import Decimal

from pydantic import BaseModel

from parsing.total_parser import SUBTOTAL, TOTAL_KEYS, _normalize, extract_amounts, is_summary_line


class LineItem(BaseModel):
    description: str
    quantity: int = 1
    price: Decimal          # price as printed on the line (line total)


# "2 x Rice 3,000.00" | "2 Rice 3000" | "Rice 1500.00" | "Rice  2 @ 750  1500"
QTY_PREFIX = re.compile(r"^\s*(\d{1,3})\s*[xX*]?\s+(?=[A-Za-z])")
TRAILING_QTY = re.compile(r"\s+\d{1,3}\s*[xX@]\s*[\d.,]+\s*$")
DATE_LIKE = re.compile(r"\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}")
PHONE_LIKE = re.compile(r"\+?\d[\d\s()-]{7,}\d")


def _looks_like_phone(line: str) -> bool:
    # A real phone number uses single spaces/hyphens, e.g. "0803 123 4567".
    # Item lines use WIDE gaps to separate the name from the price
    # ("Rice 5kg      2 x 1500.00      3000.00"), and without splitting on
    # those gaps first, the phone check spans across columns and eats
    # ordinary item lines. Split on wide gaps, then check each piece.
    return any(PHONE_LIKE.search(part) for part in re.split(r"\s{2,}", line))
NUMERIC_TOKEN = re.compile(r"^[\d.,%-]+$")


def _is_numeric_row(line: str) -> bool:
    """True if a line is (almost) entirely numbers - e.g. an item's
    'code  qty  price  amount' row printed on its own line, below the
    item's name rather than next to it."""
    tokens = line.strip().split()
    if len(tokens) < 2:
        return False
    numericish = sum(1 for t in tokens if NUMERIC_TOKEN.match(t))
    return numericish >= max(2, int(0.7 * len(tokens)))


MAX_DESC_WORDS = 7
HEADER_WORDS = {"CODE", "QTY", "PRICE", "AMOUNT", "AMT", "ITEM", "DESC", "DESCRIPTION", "NO", "NAME", "ADDRESS"}


def _is_plausible_item_desc(desc: str, letters: int) -> bool:
    if letters < 3 or letters < len(desc) // 2:
        return False                                   # not real text
    tokens = desc.split()
    if not tokens or len(tokens) > MAX_DESC_WORDS:
        return False                                   # address/header lines run long
    if tokens[0].upper().strip(".:") in HEADER_WORDS:
        return False                                   # "Code 300-C0001" -> a table header, not an item
    return True


def _clean_description(desc: str) -> tuple[str, int]:
    desc = TRAILING_QTY.sub("", desc)
    q = QTY_PREFIX.match(desc)
    qty = int(q.group(1)) if q else 1
    if q:
        desc = desc[q.end():]
    desc = re.sub(r"[^\w&'()/\-\.\s]", " ", desc)
    desc = re.sub(r"\s+", " ", desc).strip(" -._")
    return desc, qty


def _price_and_qty_from_numeric_row(line: str) -> tuple[Decimal, int] | None:
    """'88888   1   10.00   10.00' -> (price=10.00, qty=1).
    The line total is the LAST number. A long, code-like integer (the
    item/plu code) is never the quantity; the quantity is a small
    integer that isn't the price itself."""
    amounts = extract_amounts(line)
    if not amounts:
        return None
    price = amounts[-1]
    qty = 1
    for amt in amounts[:-1]:
        if amt != price and amt == amt.to_integral_value() and 0 < amt < 100:
            qty = int(amt)
            break
    return price, qty


_PRICE_AT_END_RE = re.compile(r"(\s+)([\d,]*\d(?:[.,]\d+)?)\s*$")
_LABEL_COLON = re.compile(r":\s*$")


def _price_at_end(line: str) -> str | None:
    """A trailing number counts as a price unless it's clearly something
    else: a 'Label: value' field ('LocationSP : 05'), or a bare 7+
    digit run with no separators (an invoice/reference number, not a
    formatted amount)."""
    m = _PRICE_AT_END_RE.search(line)
    if not m:
        return None
    token = m.group(2)
    prefix = line[: m.start(1)].rstrip()
    if _LABEL_COLON.search(prefix):
        return None
    if re.fullmatch(r"\d+", token) and len(token) > 6:
        return None
    return token



def _body_lines(lines: list[str]) -> list[str]:
    """Only look above the first subtotal/total line."""
    for i, line in enumerate(lines):
        u = _normalize(line)
        if SUBTOTAL.search(u) or any(p.search(u) for p, w in TOTAL_KEYS if w >= 2.0):
            return lines[:i]
    return lines


def find_line_items(text: str) -> list[LineItem]:
    lines = _body_lines([l for l in text.splitlines() if l.strip()])
    items: list[LineItem] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        if is_summary_line(line) or DATE_LIKE.search(line) or _looks_like_phone(line):
            i += 1
            continue

        stripped = line.strip()
        price_token = _price_at_end(stripped)

        if price_token is not None:
            # Case 1: description and price on the SAME line.
            amounts = extract_amounts(price_token)
            if amounts and amounts[-1] > 0:
                cut = stripped.rfind(price_token)
                desc, qty = _clean_description(stripped[:cut])
                letters = sum(c.isalpha() for c in desc)
                if _is_plausible_item_desc(desc, letters):
                    items.append(LineItem(description=desc, quantity=qty, price=amounts[-1]))
            i += 1
            continue

        # Case 2: description on THIS line, code/qty/price/amount on the NEXT
        # line (common receipt layout: item name above, numbers below).
        desc, qty = _clean_description(stripped)
        letters = sum(c.isalpha() for c in desc)
        has_description = _is_plausible_item_desc(desc, letters)
        if has_description and i + 1 < n and _is_numeric_row(lines[i + 1]) and not (
            is_summary_line(lines[i + 1])
            or DATE_LIKE.search(lines[i + 1])
            or _looks_like_phone(lines[i + 1])
        ):
            parsed = _price_and_qty_from_numeric_row(lines[i + 1])
            if parsed and parsed[0] > 0:
                price, row_qty = parsed
                items.append(LineItem(description=desc, quantity=row_qty, price=price))
                i += 2
                continue

        i += 1

    return items