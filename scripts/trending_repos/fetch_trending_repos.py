import base64
import datetime
import json
import os
import re
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
