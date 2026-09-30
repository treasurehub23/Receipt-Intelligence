from decimal import Decimal

import pytest

from parsing.total_parser import extract_info, find_total, to_decimal


@pytest.mark.parametrize(
    "token,expected",
    [
        ("12.50", "12.50"),
        ("12,50", "12.50"),
        ("1,234.50", "1234.50"),
        ("1.234,50", "1234.50"),
        ("1,234", "1234"),
        ("1,234,567.00", "1234567.00"),
    ],
)
def test_to_decimal(token, expected):
    assert to_decimal(token) == Decimal(expected)


def test_subtotal_and_tax_do_not_win():
    text = "SHOP\nSubtotal 45.00\nVAT 7.5% 3.38\nTOTAL 48.38\nCash 50.00\nChange 1.62"
    assert find_total(text).amount == Decimal("48.38")


def test_ocr_garbled_keyword():
    assert find_total("Sub-total 10.00\nT0TAL 10.50").amount == Decimal("10.50")


def test_amount_on_next_line():
    text = "Item A 5.00\nItem B 7.00\nGRAND TOTAL\n12.00"
    assert find_total(text).amount == Decimal("12.00")


def test_split_decimal():
    assert find_total("TOTAL 12 .50").amount == Decimal("12.50")


def test_total_incl_tax_is_accepted():
    text = "Item 10.00\nGST 6% 0.60\nTOTAL (INCL. GST) 10.60"
    assert find_total(text).amount == Decimal("10.60")


def test_fallback_when_no_keyword():
    r = find_total("SHOP\nfoo\nbar\nbaz 3.00\nqux 9.99")
    assert r.amount == Decimal("9.99") and r.confidence < 0.5


def test_currency_symbol_and_code():
    assert extract_info("TOTAL £12.00")["currency"] == "GBP"
    assert extract_info("Total NGN 1,500.00")["currency"] == "NGN"
    assert extract_info("TOTAL RM 12.00")["currency"] == "MYR"


def test_currency_default_is_low_confidence():
    r = extract_info("TOTAL 12.00", default_currency="NGN")
    assert r["currency"] == "NGN" and r["currency_conf"] <= 0.3


def test_naira_misread():
    r = extract_info("Rice N1,500.00\nTOTAL N1,500.00", default_currency="NGN")
    assert r["currency"] == "NGN" and r["currency_conf"] > 0.3