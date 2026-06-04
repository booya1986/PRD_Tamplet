import base64
import datetime
import json
import os
import re
import sys
import urllib.parse
import urllib.request


def iso_week_string(d):
    iso = d.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def since_date(d):
    return (d - datetime.timedelta(days=7)).isoformat()


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


SEARCH_TOPICS = ["llm", "agents", "ai-agents", "rag", "generative-ai", "mcp"]


def select_top(repos, seen, limit=10):
    by_name = {}
    for r in repos:
        name = r.get("full_name", "")
        if not name or name in seen:
            continue
        if not is_ai_relevant(r):
            continue
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
        except Exception as e:
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
