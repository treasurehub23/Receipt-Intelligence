"""Turn a parsed receipt into the text the classifier trains/predicts on.

This MUST be the same function used to build training examples and to
build the input at inference time. If training text is built one way
(e.g. 'MERCHANT item1 item2') and live text is built another way (e.g.
includes the date, or item quantities), the model learns patterns from
noise that won't exist when it's actually used - silently worse accuracy
with no obvious cause.
"""
from __future__ import annotations


def receipt_to_text(merchant: str | None, item_descriptions: list[str]) -> str:
    """merchant + item names, uppercased, concatenated.
    Mirrors generate_synthetic.py's _make_example() shape exactly."""
    parts = []
    if merchant:
        parts.append(merchant.upper())
    parts.extend(d.upper() for d in item_descriptions if d)
    return " ".join(parts)


def parsed_receipt_to_text(parsed) -> str:
    """Convenience wrapper around a ParsedReceipt object (from parse_receipt())."""
    items = [li.description for li in parsed.line_items]
    return receipt_to_text(parsed.merchant, items)