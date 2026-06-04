import datetime
from fetch_trending_repos import iso_week_string, since_date


def test_iso_week_string_formats_year_and_week():
    d = datetime.date(2026, 6, 4)  # ISO week 23 of 2026
    assert iso_week_string(d) == "2026-W23"


def test_since_date_is_seven_days_before():
    d = datetime.date(2026, 6, 4)
    assert since_date(d) == "2026-05-28"
