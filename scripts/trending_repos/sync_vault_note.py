#!/usr/bin/env python3
"""
Sync the weekly Trending AI Repos vault note from the published report.

The cloud routine cannot reach Avi's Obsidian vault, so it only writes the
report into the git repo. This local script (run by the Sunday job, which has
vault access via python3) creates a RICH bilingual vault note for the latest
week, matching the format of the hand-written W23/W24 notes.

Primary source: the committed index.html, which contains the full bilingual
briefs (What it does / Why it's trending / Example / Why it matters, he+en).
Fallback: narration.txt (thin, Hebrew-only) if HTML parsing yields nothing.

Idempotent: skips if the vault note already exists.
Usage: python3 sync_vault_note.py [week]
"""
import datetime
import html as htmllib
import os
import re
import sys

SITE_DIR = os.environ.get(
    "TRENDING_SITE_CLONE",
    os.path.expanduser("~/Documents/avi-workspace/Researches/Trending Repos/trending-site"),
)
VAULT_DIR = os.path.expanduser("~/Documents/avi-workspace/Researches/Trending Repos")
REPORTS_DIR = os.path.join(SITE_DIR, "reports")
BASE_URL = "https://booya1986.github.io/trending-ai-repos/reports"


def latest_week():
    weeks = sorted(
        d for d in os.listdir(REPORTS_DIR)
        if os.path.isdir(os.path.join(REPORTS_DIR, d)) and re.fullmatch(r"\d{4}-W\d+", d)
    )
    if not weeks:
        raise SystemExit("No report week folders found.")
    return weeks[-1]


def _unescape(s):
    # The HTML double-escapes some entities (e.g. &amp;#x27;); unescape twice.
    return htmllib.unescape(htmllib.unescape(s or "")).strip()


def parse_cards(week):
    """Extract rich per-repo data from index.html.

    Returns a list of dicts: {full_name, url, lang, stars, created, tags,
    sections: [(label_he, label_en, text_he, text_en), ...]}.
    Returns [] if the HTML cannot be parsed (caller falls back to narration).
    """
    path = os.path.join(REPORTS_DIR, week, "index.html")
    if not os.path.exists(path):
        return []
    html = open(path, encoding="utf-8").read()
    cards = []
    # Each repo is a block beginning at class="card"
    chunks = html.split('class="card"')[1:]
    for chunk in chunks:
        # Stop at the next card boundary (already split) — chunk is one card.
        m_url = re.search(r'href="(https://github\.com/[\w.\-/]+?)"', chunk)
        if not m_url:
            continue
        url = m_url.group(1).rstrip("/")
        full_name = url.split("github.com/", 1)[-1]
        lang = (re.search(r'card__eyebrow">([^<]+)<', chunk) or [None, ""])[1].strip()
        stars = (re.search(r'stars-num">([^<]+)<', chunk) or [None, ""])[1].strip()
        created = (re.search(r'meta-icon">[^<]*</span>\s*([0-9]{4}-[0-9]{2}-[0-9]{2})', chunk) or [None, ""])[1].strip()
        tags = re.findall(r'class="tag">([^<]+)<', chunk)
        # Brief sections: each has a label (he/en) then text (he/en).
        sections = []
        for sec in re.findall(
            r'brief-label"\s+data-he="(.*?)"\s+data-en="(.*?)">.*?'
            r'brief-text[^"]*"\s+data-he="(.*?)"\s+data-en="(.*?)">',
            chunk, re.DOTALL,
        ):
            label_he, label_en, text_he, text_en = (_unescape(x) for x in sec)
            sections.append((label_he, label_en, text_he, text_en))
        if sections:
            cards.append({
                "full_name": full_name, "url": url, "lang": lang,
                "stars": stars, "created": created, "tags": tags,
                "sections": sections,
            })
    return cards


def parse_narration(week):
    """Fallback: (name_he, desc_he) per repo from narration.txt."""
    path = os.path.join(REPORTS_DIR, week, "narration.txt")
    if not os.path.exists(path):
        return []
    repos = []
    for line in open(path, encoding="utf-8").read().splitlines():
        if line.startswith("מספר ") and ". " in line:
            parts = line.split(". ", 2)
            if len(parts) >= 3:
                repos.append((parts[1].strip(), parts[2].strip()))
    return repos


def _header(week):
    week_num = week.split("W")[-1]
    report_url = f"{BASE_URL}/{week}/"
    mp3_url = f"{report_url}report.mp3"
    return [
        "---",
        f"created: {datetime.date.today().isoformat()}",
        f"week: {week}",
        "tags: [trending-repos, ai, llm, research]",
        "type: weekly-digest",
        "lang: bilingual",
        "---",
        "",
        f"# 🔥 Trending AI/LLM Repos — {week}",
        "",
        f"דוח שבועי: 10 ה-repos הרלוונטיים ביותר ב-AI/LLM לשבוע {week_num}.",
        "",
        f"[📱 הדוח המלא]({report_url}) · [🎧 האזנה (עברית)]({mp3_url})",
        "",
        "---",
        "",
    ]


def build_note_rich(week, cards):
    lines = _header(week)
    for c in cards:
        tagstr = " ".join(f"`{t}`" for t in c["tags"][:6])
        lines.append(f'## [{c["full_name"]}]({c["url"]}) — `{c["lang"] or "Unknown"}`')
        if tagstr:
            lines.append(tagstr)
        stat_bits = []
        if c["stars"]:
            stat_bits.append(f'⭐ {c["stars"]}')
        if c["created"]:
            stat_bits.append(f'created {c["created"]}')
        if stat_bits:
            lines.append("")
            lines.append(f'**Stats:** {" · ".join(stat_bits)}')
        lines.append("")
        for label_he, label_en, text_he, text_en in c["sections"]:
            lines.append(f"**{label_en} / {label_he}:** {text_he}")
            lines.append("")
            lines.append(f"_{text_en}_")
            lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


def build_note_fallback(week, repos_he):
    lines = _header(week)
    for name_he, desc_he in repos_he:
        lines.append(f"## {name_he}")
        lines.append("")
        lines.append(f"**מה זה עושה:** {desc_he}")
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


def main():
    week = sys.argv[1] if len(sys.argv) > 1 else latest_week()
    note_path = os.path.join(VAULT_DIR, f"{week} Trending AI Repos.md")
    if os.path.exists(note_path):
        print(f"Vault note already exists for {week}, skipping.")
        return

    cards = parse_cards(week)
    if cards:
        content = build_note_rich(week, cards)
        print(f"Built RICH note from HTML: {len(cards)} repos.")
    else:
        repos_he = parse_narration(week)
        if not repos_he:
            print(f"No parseable HTML or narration for {week}, skipping vault note.")
            return
        content = build_note_fallback(week, repos_he)
        print(f"HTML parse empty -> fell back to narration: {len(repos_he)} repos.")

    open(note_path, "w", encoding="utf-8").write(content)
    print(f"Vault note written: {note_path}")


if __name__ == "__main__":
    main()
