# Weekly Trending AI/LLM Repos Brief — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an automation that weekly fetches trending AI/LLM GitHub repos and writes a brief (with a concrete example use case) for each into the Obsidian vault.

**Architecture:** A Python script (`fetch_trending_repos.py`) does the deterministic, brittle work — query GitHub's Search API for AI/LLM repos created in the last 7 days sorted by stars, fetch each repo's README excerpt, dedup against recent weekly notes, and emit clean JSON. A slash command (`/trending-ai-repos`) orchestrates: run the script, then Claude reads the JSON and composes the standard briefs (which require judgment — summaries, "why it matters," and concrete use cases tied to Avi's work), and writes the dated note. A scheduled routine calls the command every Friday 16:00.

**Tech Stack:** Python 3 (stdlib only: `urllib`, `json`, `base64`, `datetime`), GitHub Search API (unauthenticated), Claude Code slash command, Claude `/schedule` routine.

---

## File Structure

- `scripts/trending_repos/fetch_trending_repos.py` — fetches + dedups + emits JSON. Pure data, no prose. Lives in the vault repo under `scripts/` (force-added past the `*.md`-only-friendly gitignore; `.py` is not ignored).
- `scripts/trending_repos/test_fetch_trending_repos.py` — unit tests for the script's pure helpers (parsing, dedup, week-string, filtering). Network calls are not unit-tested; a live smoke check is a manual step.
- `~/.claude/commands/trending-ai-repos.md` — the slash command that orchestrates the run and writes the note.
- Output (runtime, not source): `Researches/Trending Repos/YYYY-Www Trending AI Repos.md`.

**Note on Python availability:** `python3` is confirmed present (used during design). Script uses stdlib only — no pip install needed.

---

### Task 1: Project scaffold and week-string helper

**Files:**
- Create: `scripts/trending_repos/fetch_trending_repos.py`
- Test: `scripts/trending_repos/test_fetch_trending_repos.py`

- [ ] **Step 1: Write the failing test**

```python
# scripts/trending_repos/test_fetch_trending_repos.py
import datetime
from fetch_trending_repos import iso_week_string, since_date

def test_iso_week_string_formats_year_and_week():
    d = datetime.date(2026, 6, 4)  # ISO week 23 of 2026
    assert iso_week_string(d) == "2026-W23"

def test_since_date_is_seven_days_before():
    d = datetime.date(2026, 6, 4)
    assert since_date(d) == "2026-05-28"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd scripts/trending_repos && python3 -m pytest test_fetch_trending_repos.py -v`
(If pytest is unavailable, run: `python3 -m unittest` after wrapping — but prefer `python3 -m pytest`. If pytest missing, install is out of scope; use `python3 -c "import fetch_trending_repos"` style asserts instead.)
Expected: FAIL with `ModuleNotFoundError: No module named 'fetch_trending_repos'`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/trending_repos/fetch_trending_repos.py
import datetime

def iso_week_string(d):
    iso = d.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"

def since_date(d):
    return (d - datetime.timedelta(days=7)).isoformat()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd scripts/trending_repos && python3 -m pytest test_fetch_trending_repos.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add -f scripts/trending_repos/fetch_trending_repos.py scripts/trending_repos/test_fetch_trending_repos.py
git commit -m "feat(trending): add week-string and since-date helpers"
```

---

### Task 2: AI/LLM relevance filter

**Files:**
- Modify: `scripts/trending_repos/fetch_trending_repos.py`
- Test: `scripts/trending_repos/test_fetch_trending_repos.py`

- [ ] **Step 1: Write the failing test**

```python
# append to test_fetch_trending_repos.py
from fetch_trending_repos import is_ai_relevant

def test_relevant_when_topic_matches():
    repo = {"name": "x", "description": "a tool", "topics": ["llm", "cli"]}
    assert is_ai_relevant(repo) is True

def test_relevant_when_description_has_keyword():
    repo = {"name": "x", "description": "An agent framework for RAG", "topics": []}
    assert is_ai_relevant(repo) is True

def test_irrelevant_when_no_signal():
    repo = {"name": "csv-parser", "description": "fast csv parsing", "topics": ["parser"]}
    assert is_ai_relevant(repo) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd scripts/trending_repos && python3 -m pytest test_fetch_trending_repos.py -v -k relevant`
Expected: FAIL with `ImportError: cannot import name 'is_ai_relevant'`

- [ ] **Step 3: Write minimal implementation**

```python
# append to fetch_trending_repos.py
AI_TOPICS = {
    "llm", "agents", "ai-agents", "rag", "machine-learning",
    "generative-ai", "llmops", "mcp", "prompt-engineering",
    "ai", "deep-learning", "transformers", "agent",
}
AI_KEYWORDS = (
    "llm", "agent", "rag", "machine learning", "generative",
    "gpt", "transformer", "neural", "prompt", "inference",
    "fine-tun", "embedding", "diffusion", "ai ",
)

def is_ai_relevant(repo):
    topics = {t.lower() for t in (repo.get("topics") or [])}
    if topics & AI_TOPICS:
        return True
    text = ((repo.get("description") or "") + " " + (repo.get("name") or "")).lower()
    return any(k in text for k in AI_KEYWORDS)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd scripts/trending_repos && python3 -m pytest test_fetch_trending_repos.py -v -k relevant`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add -f scripts/trending_repos/fetch_trending_repos.py scripts/trending_repos/test_fetch_trending_repos.py
git commit -m "feat(trending): add AI/LLM relevance filter"
```

---

### Task 3: Cross-week dedup against recent notes

**Files:**
- Modify: `scripts/trending_repos/fetch_trending_repos.py`
- Test: `scripts/trending_repos/test_fetch_trending_repos.py`

- [ ] **Step 1: Write the failing test**

```python
# append to test_fetch_trending_repos.py
from fetch_trending_repos import previously_seen_repos

def test_extracts_full_names_from_note_text(tmp_path):
    note = tmp_path / "2026-W22 Trending AI Repos.md"
    note.write_text("## [foo/bar](https://github.com/foo/bar) — `Python`\nstuff\n"
                    "## [baz/qux](https://github.com/baz/qux) — `Go`\n")
    seen = previously_seen_repos(str(tmp_path), limit=5)
    assert seen == {"foo/bar", "baz/qux"}

def test_returns_empty_for_missing_dir():
    assert previously_seen_repos("/nonexistent/path/xyz", limit=5) == set()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd scripts/trending_repos && python3 -m pytest test_fetch_trending_repos.py -v -k seen`
Expected: FAIL with `ImportError: cannot import name 'previously_seen_repos'`

- [ ] **Step 3: Write minimal implementation**

```python
# append to fetch_trending_repos.py
import os
import re

_GH_LINK = re.compile(r"github\.com/([^/\s)]+/[^/\s)]+)")

def previously_seen_repos(notes_dir, limit=3):
    if not os.path.isdir(notes_dir):
        return set()
    files = sorted(
        (f for f in os.listdir(notes_dir) if f.endswith(".md")),
        reverse=True,
    )[:limit]
    seen = set()
    for fname in files:
        try:
            with open(os.path.join(notes_dir, fname), encoding="utf-8") as fh:
                for m in _GH_LINK.finditer(fh.read()):
                    seen.add(m.group(1).rstrip(")"))
        except OSError:
            continue
    return seen
```

Note: the `rstrip(")")` guards against a trailing paren captured from a markdown link like `[name](https://github.com/foo/bar)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd scripts/trending_repos && python3 -m pytest test_fetch_trending_repos.py -v -k seen`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add -f scripts/trending_repos/fetch_trending_repos.py scripts/trending_repos/test_fetch_trending_repos.py
git commit -m "feat(trending): add cross-week dedup from recent notes"
```

---

### Task 4: GitHub API client functions (search + README)

**Files:**
- Modify: `scripts/trending_repos/fetch_trending_repos.py`
- Test: manual smoke test (network), no unit test for live calls

- [ ] **Step 1: Write the implementation**

```python
# append to fetch_trending_repos.py
import base64
import json
import urllib.request
import urllib.parse

_API = "https://api.github.com"
_HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "trending-ai-repos-script",
}

def _get(url):
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

def search_trending(since, topic, per_page=30):
    q = urllib.parse.quote(f"topic:{topic} created:>={since}")
    url = f"{_API}/search/repositories?q={q}&sort=stars&order=desc&per_page={per_page}"
    return _get(url).get("items", [])

def fetch_readme_excerpt(full_name, max_chars=4000):
    try:
        data = _get(f"{_API}/repos/{full_name}/readme")
        content = base64.b64decode(data.get("content", "")).decode("utf-8", "ignore")
        return content[:max_chars]
    except Exception:
        return ""
```

- [ ] **Step 2: Smoke test the search call live**

Run:
```bash
cd scripts/trending_repos && python3 -c "
import datetime, fetch_trending_repos as m
since = m.since_date(datetime.date.today())
items = m.search_trending(since, 'llm', per_page=3)
print('got', len(items), 'items')
print(items[0]['full_name'] if items else 'NONE')
"
```
Expected: prints `got 3 items` and a repo full_name. (If rate-limited — HTTP 403 — wait 60s and retry; unauthenticated search is 10/min.)

- [ ] **Step 3: Smoke test the README call live**

Run:
```bash
cd scripts/trending_repos && python3 -c "
import fetch_trending_repos as m
print(len(m.fetch_readme_excerpt('Significant-Gravitas/AutoGPT')), 'chars')
"
```
Expected: prints a non-zero char count (e.g. `4000 chars`).

- [ ] **Step 4: Commit**

```bash
git add -f scripts/trending_repos/fetch_trending_repos.py
git commit -m "feat(trending): add GitHub search and README client functions"
```

---

### Task 5: Normalize a repo into brief-ready JSON

**Files:**
- Modify: `scripts/trending_repos/fetch_trending_repos.py`
- Test: `scripts/trending_repos/test_fetch_trending_repos.py`

- [ ] **Step 1: Write the failing test**

```python
# append to test_fetch_trending_repos.py
from fetch_trending_repos import normalize_repo

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd scripts/trending_repos && python3 -m pytest test_fetch_trending_repos.py -v -k normalize`
Expected: FAIL with `ImportError: cannot import name 'normalize_repo'`

- [ ] **Step 3: Write minimal implementation**

```python
# append to fetch_trending_repos.py
def normalize_repo(raw, readme=""):
    pushed = (raw.get("pushed_at") or "")[:10]
    created = (raw.get("created_at") or "")[:10]
    return {
        "full_name": raw.get("full_name", ""),
        "url": raw.get("html_url", ""),
        "description": raw.get("description") or "",
        "stars": raw.get("stargazers_count", 0) or 0,
        "language": raw.get("language") or "Unknown",
        "topics": list(raw.get("topics") or []),
        "pushed_at": pushed,
        "created_at": created,
        "readme_excerpt": readme,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd scripts/trending_repos && python3 -m pytest test_fetch_trending_repos.py -v -k normalize`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add -f scripts/trending_repos/fetch_trending_repos.py scripts/trending_repos/test_fetch_trending_repos.py
git commit -m "feat(trending): normalize raw repo into brief-ready dict"
```

---

### Task 6: Orchestration `main()` — gather, filter, dedup, top 10, emit JSON

**Files:**
- Modify: `scripts/trending_repos/fetch_trending_repos.py`
- Test: `scripts/trending_repos/test_fetch_trending_repos.py` (for the pure `select_top` helper) + manual end-to-end smoke

- [ ] **Step 1: Write the failing test for the pure selection helper**

```python
# append to test_fetch_trending_repos.py
from fetch_trending_repos import select_top

def test_select_top_dedups_filters_and_limits():
    repos = [
        {"full_name": "a/llm", "description": "an llm tool", "topics": ["llm"], "stargazers_count": 500},
        {"full_name": "a/llm", "description": "an llm tool", "topics": ["llm"], "stargazers_count": 500},  # dup full_name
        {"full_name": "b/csv", "description": "csv parser", "topics": ["parser"], "stargazers_count": 999},  # not AI
        {"full_name": "c/agent", "description": "agent framework", "topics": ["agents"], "stargazers_count": 100},
    ]
    out = select_top(repos, seen={"c/agent"}, limit=10)
    names = [r["full_name"] for r in out]
    assert names == ["a/llm"]  # dup collapsed, csv filtered (not AI), c/agent removed (already seen)

def test_select_top_sorts_by_stars_desc_and_limits():
    repos = [
        {"full_name": "x/llm1", "description": "llm", "topics": ["llm"], "stargazers_count": 10},
        {"full_name": "y/llm2", "description": "llm", "topics": ["llm"], "stargazers_count": 50},
        {"full_name": "z/llm3", "description": "llm", "topics": ["llm"], "stargazers_count": 30},
    ]
    out = select_top(repos, seen=set(), limit=2)
    assert [r["full_name"] for r in out] == ["y/llm2", "z/llm3"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd scripts/trending_repos && python3 -m pytest test_fetch_trending_repos.py -v -k select_top`
Expected: FAIL with `ImportError: cannot import name 'select_top'`

- [ ] **Step 3: Write the `select_top` helper and `main()`**

```python
# append to fetch_trending_repos.py
import sys

SEARCH_TOPICS = ["llm", "agents", "ai-agents", "rag", "generative-ai", "mcp"]

def select_top(repos, seen, limit=10):
    by_name = {}
    for r in repos:
        name = r.get("full_name", "")
        if not name or name in seen:
            continue
        if not is_ai_relevant(r):
            continue
        # keep the higher-star copy if duplicate
        if name not in by_name or (r.get("stargazers_count", 0) or 0) > (by_name[name].get("stargazers_count", 0) or 0):
            by_name[name] = r
    ranked = sorted(by_name.values(), key=lambda r: r.get("stargazers_count", 0) or 0, reverse=True)
    return ranked[:limit]

def main():
    today = datetime.date.today()
    since = since_date(today)
    week = iso_week_string(today)
    notes_dir = os.path.expanduser(
        "~/Documents/avi-workspace/Researches/Trending Repos"
    )
    seen = previously_seen_repos(notes_dir, limit=3)

    warnings = []
    collected = []
    for topic in SEARCH_TOPICS:
        try:
            collected.extend(search_trending(since, topic, per_page=30))
        except Exception as e:  # noqa: BLE001 — network/rate-limit, keep going
            warnings.append(f"search failed for topic '{topic}': {e}")

    top = select_top(collected, seen=seen, limit=10)
    if len(top) < 10:
        warnings.append(f"only {len(top)} AI/LLM repos found (wanted 10)")

    briefs = []
    for r in top:
        readme = fetch_readme_excerpt(r.get("full_name", ""))
        if not readme:
            warnings.append(f"no README for {r.get('full_name')}")
        briefs.append(normalize_repo(r, readme=readme))

    out = {
        "week": week,
        "since": since,
        "generated_for": today.isoformat(),
        "notes_dir": notes_dir,
        "count": len(briefs),
        "warnings": warnings,
        "repos": briefs,
    }
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run unit test to verify select_top passes**

Run: `cd scripts/trending_repos && python3 -m pytest test_fetch_trending_repos.py -v -k select_top`
Expected: PASS (2 passed)

- [ ] **Step 5: Run the full test suite**

Run: `cd scripts/trending_repos && python3 -m pytest test_fetch_trending_repos.py -v`
Expected: PASS (all tests from Tasks 1-6)

- [ ] **Step 6: End-to-end smoke test (live network)**

Run:
```bash
cd scripts/trending_repos && python3 fetch_trending_repos.py > /tmp/trending.json && python3 -c "
import json; d=json.load(open('/tmp/trending.json'))
print('week:', d['week'], '| count:', d['count'], '| warnings:', len(d['warnings']))
for r in d['repos'][:3]:
    print('-', r['full_name'], r['stars'], '★', '| readme', len(r['readme_excerpt']), 'chars')
"
```
Expected: prints the week (e.g. `2026-W23`), a count (ideally 10), and the first few repos with star counts and README lengths. Some warnings are acceptable (rate limits). If count is 0, wait 60s for rate-limit reset and retry.

- [ ] **Step 7: Commit**

```bash
git add -f scripts/trending_repos/fetch_trending_repos.py scripts/trending_repos/test_fetch_trending_repos.py
git commit -m "feat(trending): add orchestration main() emitting brief-ready JSON"
```

---

### Task 7: The `/trending-ai-repos` slash command

**Files:**
- Create: `~/.claude/commands/trending-ai-repos.md`

- [ ] **Step 1: Write the command file**

Create `~/.claude/commands/trending-ai-repos.md` with this exact content:

````markdown
Generate this week's Trending AI/LLM Repos brief and save it to the Obsidian vault.

## Steps

1. Run the fetch script and capture its JSON output:

```bash
python3 ~/Documents/avi-workspace/scripts/trending_repos/fetch_trending_repos.py
```

The JSON has: `week` (e.g. `2026-W23`), `since`, `count`, `warnings` (array), `notes_dir`, and `repos` (array). Each repo has: `full_name`, `url`, `description`, `stars`, `language`, `topics`, `pushed_at`, `created_at`, `readme_excerpt`.

2. For EACH repo in `repos`, write a **standard brief** grounded in its `description` and `readme_excerpt` (do not invent features — if the README excerpt is empty, write a thinner brief from metadata and note it). Use exactly this template per repo:

```markdown
## [<full_name>](<url>) — `<language>`
<space-separated `topic` tags, max 4>

**Stats:** ⭐ <stars> · created <created_at> · last push <pushed_at>

**What it does:** <2-3 sentences, grounded in the README excerpt>

**Why it's trending:** <who it's for and why it's getting attention now>

**Example use case:** <a concrete, specific scenario showing how Avi could use it, tied to his AI / L&D / content / Poalim work where it genuinely fits; otherwise a neutral, specific general-purpose example>

**Why it matters for you:** <one short tie-in line>
```

3. Compose the full note:
   - Frontmatter:
     ```yaml
     ---
     created: <generated_for>
     week: <week>
     tags: [trending-repos, ai, llm, research]
     type: weekly-digest
     ---
     ```
   - An H1 title: `# 🔥 Trending AI/LLM Repos — <week>`
   - A 1-2 line intro summarizing the week's theme (what kinds of tools dominated).
   - If `warnings` is non-empty, add a short `> [!note] Run notes` callout listing them (so failures are never silent).
   - Then all the repo briefs in order.

4. Save the note to: `<notes_dir>/<week> Trending AI Repos.md`
   (e.g. `~/Documents/avi-workspace/Researches/Trending Repos/2026-W23 Trending AI Repos.md`). Use the Write tool. Create the file (overwrite if a same-week file exists).

5. Confirm to the user: the path written, the number of repos, and any warnings.

## Notes
- Never touch `the-system-v8/` or anything outside `Researches/Trending Repos/`.
- If the script outputs `count: 0`, it is likely a GitHub rate limit — tell the user to retry in a minute rather than writing an empty note.
````

- [ ] **Step 2: Verify the command is recognized**

Run: `ls -la ~/.claude/commands/trending-ai-repos.md`
Expected: file exists. (Slash commands are picked up from this dir; `/trending-ai-repos` will be available.)

- [ ] **Step 3: Commit the script changes (command file lives in ~/.claude, outside the repo — not committed)**

No repo commit needed for this task; the command file is in `~/.claude/commands/` which is gitignored in the vault. Note this in the handoff so the user knows the command isn't version-controlled with the vault.

---

### Task 8: First run — generate this week's note now

**Files:**
- Output: `Researches/Trending Repos/2026-W23 Trending AI Repos.md` (or current week)

- [ ] **Step 1: Run the slash command**

Invoke `/trending-ai-repos` in this session.
Expected: a note is written to `Researches/Trending Repos/<week> Trending AI Repos.md` with up to 10 briefs, each having all six sections including a concrete example use case.

- [ ] **Step 2: Verify the output note**

Run:
```bash
ls -la ~/Documents/avi-workspace/Researches/Trending\ Repos/ && head -40 ~/Documents/avi-workspace/Researches/Trending\ Repos/*Trending\ AI\ Repos.md
```
Expected: the dated file exists; frontmatter, title, intro, and at least the first brief render correctly with all six sections.

- [ ] **Step 3: Spot-check grounding**

Read the first brief and confirm "What it does" matches the repo's actual README/description (no invented features). If any brief is ungrounded, regenerate that brief.

---

### Task 9: Register the weekly Friday 16:00 schedule

**Files:**
- Schedule/routine config (managed via the `/schedule` skill)

- [ ] **Step 1: Confirm the scheduling mechanism and vault reachability**

Use the `schedule` skill to create a routine. Before finalizing, confirm whether the scheduled (possibly remote) run can reach the local vault path `~/Documents/avi-workspace/Researches/Trending Repos/`. This is the design's known risk.
- If reachable: schedule the routine to invoke `/trending-ai-repos` every Friday at 16:00, starting next Friday.
- If NOT reachable from a remote run: fall back to a local recurring trigger (e.g. a `/loop`-style or local cron calling the command), OR set a recurring calendar reminder for Avi to run `/trending-ai-repos` manually each Friday. Tell the user which fallback is in effect and why.

- [ ] **Step 2: Verify the schedule exists**

List scheduled routines and confirm the Friday 16:00 entry is present with the correct command. Report the next fire time to the user.

- [ ] **Step 3: Confirm first scheduled run is NEXT Friday**

Confirm the schedule's first execution is the following Friday 16:00 (not today), since today's run was handled manually in Task 8.

---

### Task 10: Cleanup — remove the design and plan specs

**Files:**
- Delete: `docs/superpowers/specs/2026-06-04-trending-ai-repos-design.md`
- Delete: `docs/superpowers/plans/2026-06-04-trending-ai-repos.md` (this file)

Per the user's instruction ("delete the spec after it's done"), remove the spec once everything above is complete and verified.

- [ ] **Step 1: Delete the spec and plan files**

```bash
git rm -f docs/superpowers/specs/2026-06-04-trending-ai-repos-design.md
rm -f docs/superpowers/plans/2026-06-04-trending-ai-repos.md
```
(The plan file was force-added; if it was committed, use `git rm -f` for it too.)

- [ ] **Step 2: Commit the cleanup**

```bash
git commit -m "chore(trending): remove design spec and plan after implementation"
```

- [ ] **Step 3: Confirm to the user**

Report: skill/command built and tested, this week's note generated, weekly schedule registered (or fallback in effect), and specs removed.

---

## Self-Review

**Spec coverage:**
- AI/LLM scope → Tasks 2, 6 (`is_ai_relevant`, `SEARCH_TOPICS`). ✓
- Output to `Researches/Trending Repos/` dated note → Tasks 6, 7. ✓
- Standard brief + concrete example use case → Task 7 template (six sections). ✓
- Trigger via scheduled routine calling reusable command → Tasks 7, 9. ✓
- Top 10 → Task 6 (`select_top(..., limit=10)`). ✓
- One dated note per week → Task 7 (`<week> Trending AI Repos.md`). ✓
- First run now → Task 8. ✓
- Recurring Friday 16:00 starting next week → Task 9. ✓
- README-grounded summaries → Tasks 4, 5, 7. ✓
- Cross-week dedup → Tasks 3, 6. ✓
- Never-silent failure (warnings surfaced) → Task 6 (`warnings`), Task 7 (callout). ✓
- Excludes `the-system-v8/` → Task 7 Notes; script only ever reads/writes `Researches/Trending Repos/`. ✓
- Remote-scheduling caveat + fallback → Task 9. ✓
- Delete spec when done → Task 10. ✓

**Placeholder scan:** No TBD/TODO. Every code step has complete code; every brief section is specified. The one self-correction (the `if False` line in Task 3) is explicitly flagged and replaced inline.

**Type consistency:** JSON keys emitted by `normalize_repo`/`main` (`full_name`, `url`, `description`, `stars`, `language`, `topics`, `pushed_at`, `created_at`, `readme_excerpt`, and top-level `week`, `since`, `generated_for`, `notes_dir`, `count`, `warnings`, `repos`) match exactly what the Task 7 command consumes. `select_top`, `is_ai_relevant`, `previously_seen_repos`, `search_trending`, `fetch_readme_excerpt`, `normalize_repo`, `iso_week_string`, `since_date` names are consistent across all tasks. ✓
