import datetime
from fetch_trending_repos import iso_week_string, since_date
from fetch_trending_repos import is_ai_relevant
from fetch_trending_repos import previously_seen_repos
from fetch_trending_repos import normalize_repo
from fetch_trending_repos import select_top
from fetch_trending_repos import interest_score, is_relevant


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


def test_extracts_full_names_from_note_text(tmp_path):
    note = tmp_path / "2026-W22 Trending AI Repos.md"
    note.write_text("## [foo/bar](https://github.com/foo/bar) — `Python`\nstuff\n"
                    "## [baz/qux](https://github.com/baz/qux) — `Go`\n")
    seen = previously_seen_repos(str(tmp_path), limit=5)
    assert seen == {"foo/bar", "baz/qux"}


def test_returns_empty_for_missing_dir():
    assert previously_seen_repos("/nonexistent/path/xyz", limit=5) == set()


def test_normalize_extracts_expected_fields():
    raw = {
        "full_name": "foo/bar",
        "html_url": "https://github.com/foo/bar",
        "description": "An LLM agent toolkit",
        "stargazers_count": 1234,
        "language": "Python",
        "topics": ["llm", "agents"],
        "pushed_at": "2026-06-03T10:00:00Z",
        "created_at": "2026-05-30T10:00:00Z",
    }
    out = normalize_repo(raw, readme="# Title\nHello")
    assert out["full_name"] == "foo/bar"
    assert out["url"] == "https://github.com/foo/bar"
    assert out["stars"] == 1234
    assert out["language"] == "Python"
    assert out["topics"] == ["llm", "agents"]
    assert out["description"] == "An LLM agent toolkit"
    assert out["pushed_at"] == "2026-06-03"
    assert out["readme_excerpt"] == "# Title\nHello"


def test_normalize_handles_missing_fields():
    out = normalize_repo({"full_name": "a/b"}, readme="")
    assert out["language"] == "Unknown"
    assert out["topics"] == []
    assert out["description"] == ""
    assert out["stars"] == 0


def test_select_top_dedups_filters_and_limits():
    repos = [
        {"full_name": "a/llm", "description": "an llm tool", "topics": ["llm"], "stargazers_count": 500},
        {"full_name": "a/llm", "description": "an llm tool", "topics": ["llm"], "stargazers_count": 500},
        {"full_name": "b/csv", "description": "csv parser", "topics": ["parser"], "stargazers_count": 999},
        {"full_name": "c/agent", "description": "agent framework", "topics": ["agents"], "stargazers_count": 100},
    ]
    out = select_top(repos, seen={"c/agent"}, limit=10)
    names = [r["full_name"] for r in out]
    assert names == ["a/llm"]


def test_select_top_sorts_by_stars_desc_and_limits():
    repos = [
        {"full_name": "x/llm1", "description": "llm", "topics": ["llm"], "stargazers_count": 10},
        {"full_name": "y/llm2", "description": "llm", "topics": ["llm"], "stargazers_count": 50},
        {"full_name": "z/llm3", "description": "llm", "topics": ["llm"], "stargazers_count": 30},
    ]
    out = select_top(repos, seen=set(), limit=2)
    assert [r["full_name"] for r in out] == ["y/llm2", "z/llm3"]


def test_select_top_keeps_higher_star_copy_on_duplicate():
    repos = [
        {"full_name": "dup/repo", "description": "llm", "topics": ["llm"], "stargazers_count": 500},
        {"full_name": "dup/repo", "description": "llm", "topics": ["llm"], "stargazers_count": 800},
    ]
    out = select_top(repos, seen=set(), limit=10)
    assert len(out) == 1
    assert out[0]["stargazers_count"] == 800


def test_interest_score_counts_distinct_signals():
    # "agent", "rag", and "obsidian" are all interest signals.
    repo = {"name": "x", "description": "an agent for rag over obsidian", "topics": []}
    assert interest_score(repo) >= 3
    plain = {"name": "y", "description": "a csv parser", "topics": []}
    assert interest_score(plain) == 0


def test_is_relevant_drops_anti_signal_with_no_interest():
    # AI-relevant by keyword but dominated by an anti-signal, no interest match.
    repo = {"name": "z", "description": "an llm deepfake face-swap tool", "topics": ["llm"]}
    assert is_relevant(repo) is False


def test_is_relevant_keeps_anti_signal_when_interest_present():
    # Anti-signal present but also a genuine interest match -> keep.
    repo = {"name": "z", "description": "an agent that detects deepfake for learning", "topics": ["agents"]}
    assert is_relevant(repo) is True


def test_select_top_applies_star_floor():
    # Two repos clear the 50-star floor, one does not; with enough candidates
    # the sub-floor repo is excluded.
    repos = [
        {"full_name": "a/agent", "description": "agent rag llm", "topics": ["agents"], "stargazers_count": 80},
        {"full_name": "b/agent", "description": "agent rag llm", "topics": ["agents"], "stargazers_count": 60},
    ] + [
        {"full_name": f"f/repo{i}", "description": "agent rag llm", "topics": ["agents"], "stargazers_count": 70 + i}
        for i in range(10)
    ] + [
        {"full_name": "low/repo", "description": "agent rag llm", "topics": ["agents"], "stargazers_count": 5},
    ]
    out = select_top(repos, seen=set(), limit=10)
    names = {r["full_name"] for r in out}
    assert "low/repo" not in names
    assert all((r.get("stargazers_count") or 0) >= 50 for r in out)


def test_select_top_relevance_leads_stars_break_ties():
    # Lower-star but more-relevant repo ranks above a higher-star less-relevant one.
    repos = [
        {"full_name": "rich/generic", "description": "an llm tool", "topics": ["llm"], "stargazers_count": 900},
        {"full_name": "poor/relevant", "description": "agent rag obsidian skill workflow memory", "topics": ["agents", "rag", "mcp"], "stargazers_count": 60},
    ]
    out = select_top(repos, seen=set(), limit=10)
    assert out[0]["full_name"] == "poor/relevant"


def test_select_top_lowers_floor_when_too_few_qualify():
    # Only a few clear 50; fallback should fill the list and warn.
    repos = [
        {"full_name": "hi/one", "description": "agent llm", "topics": ["agents"], "stargazers_count": 90},
    ] + [
        {"full_name": f"mid/repo{i}", "description": "agent llm", "topics": ["agents"], "stargazers_count": 12 + i}
        for i in range(8)
    ]
    warnings = []
    out = select_top(repos, seen=set(), limit=10, warnings=warnings)
    assert len(out) == 9
    assert any("lowered" in w for w in warnings)
