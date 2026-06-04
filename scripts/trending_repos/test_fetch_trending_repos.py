import datetime
from fetch_trending_repos import iso_week_string, since_date
from fetch_trending_repos import is_ai_relevant


def test_iso_week_string_formats_year_and_week():
    d = datetime.date(2026, 6, 4)  # ISO week 23 of 2026
    assert iso_week_string(d) == "2026-W23"


def test_since_date_is_seven_days_before():
    d = datetime.date(2026, 6, 4)
    assert since_date(d) == "2026-05-28"


def test_relevant_when_topic_matches():
    repo = {"name": "x", "description": "a tool", "topics": ["llm", "cli"]}
    assert is_ai_relevant(repo) is True


def test_relevant_when_description_has_keyword():
    repo = {"name": "x", "description": "An agent framework for RAG", "topics": []}
    assert is_ai_relevant(repo) is True


def test_irrelevant_when_no_signal():
    repo = {"name": "csv-parser", "description": "fast csv parsing", "topics": ["parser"]}
    assert is_ai_relevant(repo) is False
