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

# Avi's interest signals, derived from a vault review. Repos matching more of
# these rank higher (see interest_score). Grouped only for readability.
INTEREST_SIGNALS = (
    # Agent skills, workflows, multi-agent, MCP
    "agent", "agents", "agentic", "multi-agent", "orchestrat", "mcp",
    "claude", "claude-code", "skill", "skills", "workflow", "autonomous",
    "agent-memory", "human-in-the-loop", "tool-use", "harness",
    # Prompt / context engineering
    "prompt", "context engineering", "context-engineering", "system prompt",
    "instruction",
    # RAG, knowledge, memory, Obsidian, PKM
    "rag", "retrieval", "vector", "semantic search", "semantic-search",
    "knowledge base", "knowledge-base", "knowledge management", "memory",
    "persistent memory", "second brain", "obsidian", "pkm", "note", "notes",
    "embedding",
    # Gen AI for content, video, audio, TTS
    "text-to-speech", "text to speech", "tts", "speech", "voice",
    "transcription", "diarization", "video", "audio", "subtitle", "caption",
    "content", "generative",
    # Learning / education / L&D
    "edtech", "instructional", "learning", "education", "course",
    "training", "teach", "tutor", "curriculum", "learn",
    # Vibe coding / build-with-AI / learn-to-build
    "vibe", "no-code", "low-code", "code generation", "code-gen", "scaffold",
    "from scratch", "nanogpt", "build your own", "minimal", "explained",
    # Local-first / privacy / governance
    "local-first", "on-device", "privacy", "self-host", "governance",
)

# Topics/keywords that look AI-adjacent but are NOT Avi's interest. A repo whose
# signal is dominated by these is dropped (see is_relevant).
ANTI_SIGNALS = (
    "crypto", "blockchain", "web3", "trading-bot", "robot", "robotics",
    "game", "gaming", "anti-detect", "antidetect", "scraper", "scraping",
    "deepfake", "face-swap", "faceswap",
)


def _repo_text(repo):
    topics = " ".join(repo.get("topics") or [])
    return (
        (repo.get("name") or "") + " "
        + (repo.get("description") or "") + " "
        + topics
    ).lower()


def is_ai_relevant(repo):
    topics = {t.lower() for t in (repo.get("topics") or [])}
    if topics & AI_TOPICS:
        return True
    text = ((repo.get("description") or "") + " " + (repo.get("name") or "")).lower()
    return any(k in text for k in AI_KEYWORDS)


def interest_score(repo):
    """Count distinct interest signals present in the repo's text."""
    text = _repo_text(repo)
    return sum(1 for sig in INTEREST_SIGNALS if sig in text)


def anti_score(repo):
    text = _repo_text(repo)
    return sum(1 for sig in ANTI_SIGNALS if sig in text)


def is_relevant(repo):
    """Keep AI repos, but drop ones dominated by anti-signals with no interest match."""
    if not is_ai_relevant(repo):
        return False
    interest = interest_score(repo)
    anti = anti_score(repo)
    # Drop if it trips anti-signals and shows no real interest match.
    if anti > 0 and interest == 0:
        return False
    return True


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


def _build_headers():
    headers = dict(_HEADERS)
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _get(url):
    req = urllib.request.Request(url, headers=_build_headers())
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


SEARCH_TOPICS = [
    # core AI/LLM
    "llm", "agents", "ai-agents", "generative-ai", "mcp",
    # Avi's interest areas
    "rag", "agent-skills", "prompt-engineering", "ai-agent",
    "knowledge-management", "text-to-speech", "obsidian",
    "instructional-design", "vibe-coding", "local-llm",
]


STAR_FLOOR = 50  # a repo needs real weekly traction to count as "trending"


def select_top(repos, seen, limit=10, star_floor=STAR_FLOOR, warnings=None):
    by_name = {}
    for r in repos:
        name = r.get("full_name", "")
        if not name or name in seen:
            continue
        if not is_relevant(r):
            continue
        if name not in by_name or (r.get("stargazers_count", 0) or 0) > (by_name[name].get("stargazers_count", 0) or 0):
            by_name[name] = r

    # Relevance leads, stars break ties: sort by (interest_score, stars) desc.
    def rank_key(r):
        return (interest_score(r), r.get("stargazers_count", 0) or 0)

    def stars(r):
        return r.get("stargazers_count", 0) or 0

    qualified = [r for r in by_name.values() if stars(r) >= star_floor]

    # Graceful fallback: if too few clear the floor, lower it so the list never
    # silently shrinks, and record that we did.
    floor_used = star_floor
    if len(qualified) < limit:
        for fallback in (25, 10, 0):
            if fallback >= star_floor:
                continue
            qualified = [r for r in by_name.values() if stars(r) >= fallback]
            floor_used = fallback
            if len(qualified) >= limit:
                break
        if warnings is not None and floor_used < star_floor:
            warnings.append(
                f"only {len([r for r in by_name.values() if stars(r) >= star_floor])} "
                f"repos cleared the {star_floor}-star floor; lowered to "
                f"{floor_used} stars to fill the list"
            )

    ranked = sorted(qualified, key=rank_key, reverse=True)
    return ranked[:limit]


def main():
    today = datetime.date.today()
    since = since_date(today)
    week = iso_week_string(today)
    notes_dir = os.path.expanduser(
        os.environ.get(
            "TRENDING_NOTES_DIR",
            "~/Documents/avi-workspace/Researches/Trending Repos",
        )
    )
    seen = previously_seen_repos(notes_dir, limit=3)

    warnings = []
    collected = []
    for topic in SEARCH_TOPICS:
        try:
            collected.extend(search_trending(since, topic, per_page=30))
        except Exception as e:
            warnings.append(f"search failed for topic '{topic}': {e}")

    top = select_top(collected, seen=seen, limit=10, warnings=warnings)
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
