from datetime import date

from parsing.date_parser import find_date

TODAY = date(2026, 9, 28)


def d(text, **kw):
    return find_date(text, today=TODAY, **kw)


def test_iso_date_works_even_with_dmy_setting():
    # regression: dateparser rejects year-first dates under DATE_ORDER=DMY
    assert d("Date: 2018-05-22 Time 10:15").value == date(2018, 5, 22)


def test_day_first_slash_date():
    assert d("14/03/2026 14:32").value == date(2026, 3, 14)


def test_month_name_formats():
    assert d("DATE 03-Feb-2026").value == date(2026, 2, 3)
    assert d("Mar 9, 2026").value == date(2026, 3, 9)
    assert d("9 March 2026").value == date(2026, 3, 9)


def test_ambiguous_date_follows_date_order_with_lower_confidence():
    dmy = d("01/04/2026", date_order="DMY")
    mdy = d("01/04/2026", date_order="MDY")
    assert dmy.value == date(2026, 4, 1) and mdy.value == date(2026, 1, 4)
    assert dmy.confidence < d("14/04/2026").confidence


def test_future_and_ancient_dates_rejected():
    assert d("31/12/2099").value is None
    assert d("01/01/1970").value is None


def test_no_date():
    r = d("TOTAL 12.50\nThank you")
    assert r.value is None and r.confidence == 0.0