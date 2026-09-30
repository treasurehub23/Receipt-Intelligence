from datetime import date
from decimal import Decimal

from parsing import parse_receipt
from parsing.items_parser import find_line_items

TODAY = date(2026, 9, 28)

R01_TEXT = """SHOPRITE SUPERMARKET
Ikeja City Mall, Alausa
Tel: 0803 123 4567
Date: 14/03/2026  14:32
2 x Indomie Noodles      700.00
Peak Milk 400g         2,850.00
Bread (Large)          1,200.00
Subtotal               4,750.00
VAT 7.5%                 356.25
TOTAL                  5,106.25
"""

R04_TEXT = """QUICKMART
Order #4432
Mar 9, 2026
Sandwich          6.50
Coffee            3.25
Sub-total         9.75
Tax               0.78
Amount Due       $10.53
"""


def test_items_stop_at_totals_and_skip_summary_lines():
    text = "SHOP\n2 x Indomie Noodles 700.00\nPeak Milk 400g 2,850.00\nSubtotal 3,550.00\nTOTAL 3,550.00"
    items = find_line_items(text)
    assert [(i.description, i.quantity, i.price) for i in items] == [
        ("Indomie Noodles", 2, Decimal("700.00")),
        ("Peak Milk 400g", 1, Decimal("2850.00")),
    ]


def test_address_and_phone_lines_are_not_items():
    text = "SHOP\n12 Allen Avenue\nTel 0803 123 4567\nRice 500\nTOTAL 500"
    assert [i.description for i in find_line_items(text)] == ["Rice"]


def test_wide_column_gaps_are_not_mistaken_for_a_phone_number():
    # regression: PHONE_LIKE used to span the wide gaps receipts use to
    # separate name/qty/price columns, dropping legitimate item lines
    text = "SHOP\nRice 5kg          2 x 1500.00       3000.00\nTOTAL 3000.00"
    items = find_line_items(text)
    assert [i.description for i in items] == ["Rice 5kg"]
    assert items[0].price == Decimal("3000.00")


def test_two_row_item_layout_merges_description_and_numbers():
    # some receipts print the item name on one row and its
    # code/qty/price/amount on the row below it
    text = (
        "SHOP\n"
        "ST-PRIVILEGE CARD/GD INDAH\n"
        "88888          1    10.00   10.00\n"
        "GF-TABLE LAMP/STITCH\n"
        "62483          1    55.90   55.90\n"
        "TOTAL AMT   60.31\n"
    )
    items = find_line_items(text)
    assert [(i.description, i.price) for i in items] == [
        ("ST-PRIVILEGE CARD/GD INDAH", Decimal("10.00")),
        ("GF-TABLE LAMP/STITCH", Decimal("55.90")),
    ]


def test_label_colon_value_is_not_mistaken_for_a_price():
    # regression: "LocationSP : 05" used to become a fake item priced 5
    text = "SHOP\nCashier : CX\nLocationSP : 05\nRice 500\nTOTAL 500"
    assert [i.description for i in find_line_items(text)] == ["Rice"]


def test_phone_number_below_address_is_not_merged_into_an_item():
    # regression: a phone line under an address line looked like a
    # numeric row and got merged into a fake item
    text = "SHOP\nIkeja City Mall, Alausa\nTel: 0803 123 4567\nRice 500\nTOTAL 500"
    assert [i.description for i in find_line_items(text)] == ["Rice"]


def test_reference_number_is_not_a_price():
    text = "SHOP\nRoom No: 01                    050100035279\nRice 500\nTOTAL 500"
    assert [i.description for i in find_line_items(text)] == ["Rice"]


def test_address_line_with_trailing_postal_code_is_not_an_item():
    # regression: a 5-digit postal code at the end of a long address line
    # was short enough to slip past the "7+ digit code" guard
    text = "SHOP\nKLANG SELANGUR D. E, BANDAR BUKIT RAJA MALAYSIA 41050\nRice 500\nTOTAL 500"
    assert [i.description for i in find_line_items(text)] == ["Rice"]


def test_table_header_word_is_not_an_item_description():
    # regression: "Code 300-C0001  1" (a code/header row) became a fake
    # item named "Code 300-C0001"
    text = "SHOP\nCode 300-C0001 1\nRice 500\nTOTAL 500"
    assert [i.description for i in find_line_items(text)] == ["Rice"]


def test_full_pipeline_on_sample_receipt():
    r = parse_receipt(R01_TEXT, default_currency="NGN", today=TODAY)
    assert r.merchant == "SHOPRITE SUPERMARKET"
    assert r.purchase_date == date(2026, 3, 14)
    assert r.total == Decimal("5106.25")
    assert r.currency == "NGN"
    assert len(r.line_items) == 3
    assert r.raw_text  # always keep the OCR for debugging


def test_pipeline_never_crashes_on_garbage():
    for text in ["", "   \n\n", "~~ ## ~~", "12345", "TOTAL"]:
        r = parse_receipt(text, today=TODAY)
        assert r.total is None or isinstance(r.total, Decimal)
        assert 0.0 <= r.confidence.total <= 1.0


def test_result_serializes_to_json():
    r = parse_receipt(R04_TEXT, today=TODAY)
    assert '"total":"10.53"' in r.model_dump_json()