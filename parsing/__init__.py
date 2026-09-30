"""Receipt parsing: raw OCR text in, structured fields (with confidences) out.

Everything here is pure: text in, data out. No OCR, no I/O, no FastAPI.
That is what makes it easy to test against fixed OCR text.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from parsing.date_parser import find_date
from parsing.items_parser import LineItem, find_line_items
from parsing.merchant_parser import find_merchant
from parsing.total_parser import find_currency, find_total

__all__ = ["parse_receipt", "ParsedReceipt", "Confidence", "LineItem"]


class Confidence(BaseModel):
    merchant: float
    purchase_date: float
    total: float
    currency: float


class ParsedReceipt(BaseModel):
    """Everything in the Expense model except id, category and created_at."""

    merchant: str | None
    purchase_date: date | None
    total: Decimal | None
    currency: str
    confidence: Confidence
    line_items: list[LineItem]
    raw_text: str


def parse_receipt(
    raw_text: str,
    default_currency: str = "NGN",
    date_order: str = "DMY",
    today: date | None = None,
) -> ParsedReceipt:
    merchant = find_merchant(raw_text)
    when = find_date(raw_text, date_order=date_order, today=today)
    total = find_total(raw_text)
    currency = find_currency(raw_text, default=default_currency)

    return ParsedReceipt(
        merchant=merchant.name,
        purchase_date=when.value,
        total=total.amount,
        currency=currency.code,
        confidence=Confidence(
            merchant=merchant.confidence,
            purchase_date=when.confidence,
            total=total.confidence,
            currency=currency.confidence,
        ),
        line_items=find_line_items(raw_text),
        raw_text=raw_text,
    )