#!/usr/bin/env python3
"""Build a mobile-responsive HTML report and a narration script from fetch JSON.

Reads the JSON emitted by fetch_trending_repos.py (stdin or --in), and writes:
  - <outdir>/index.html      mobile-friendly report page (links to report.mp3)
  - <outdir>/narration.txt   plain-text narration for TTS

Design system: matches Avi's blog. Hebrew RTL default with EN toggle.
"""
import argparse
import html
import json
import os
import sys


def _tags(topics, n=4):
    return topics[:n] if topics else []


def render_html(data):
    week = data.get("week", "")
    generated_for = data.get("generated_for", "")
    repos = data.get("repos", [])
    warnings = data.get("warnings", []) or []

    cards = []
    for i, r in enumerate(repos, 1):
        name_raw = r.get("full_name", "")
        url = html.escape(r.get("url", ""))
        lang = html.escape(r.get("language") or "")
        stars = r.get("stars", 0)
        created = html.escape(r.get("created_at", ""))
        pushed = html.escape(r.get("pushed_at", ""))
        brief = r.get("brief_html")
        tag_items = _tags(r.get("topics"))
        tag_html = "".join(f'<span class="tag">{html.escape(t)}</span>' for t in tag_items)
        desc = html.escape(r.get("description") or "")
        body = brief if brief else f'<p class="desc">{desc}</p>'
        org, repo_name = (name_raw.split("/", 1) + [""])[:2]
        cards.append(f"""
    <article class="card">
      <div class="card__rank">#{i}</div>
      <div class="card__body">

        <div class="card__header">
          <div class="card__title-block">
            <p class="card__eyebrow">{lang}</p>
            <h2 class="card__title">
              <a href="{url}" target="_blank" rel="noopener">
                <span class="card__org">{html.escape(org)}/</span>{html.escape(repo_name)}
              </a>
            </h2>
          </div>
          <div class="card__stats">
            <span class="card__stars">&#9733;<br><span class="stars-num">{stars:,}</span></span>
          </div>
        </div>

        <div class="card__meta">
          <span class="meta-item"><span class="meta-icon">&#128197;</span> {created}</span>
          <span class="meta-item"><span class="meta-icon">&#9679;</span> push {pushed}</span>
        </div>

        <div class="card__tags">{tag_html}</div>

        <div class="card__content">{body}</div>

      </div>
    </article>""")

    warn_html = ""
    if warnings:
        items = "".join(f"<li>{html.escape(w)}</li>" for w in warnings)
        warn_html = f'<div class="run-notes"><strong class="i18n" data-he="הערות ריצה" data-en="Run notes">הערות ריצה</strong><ul>{items}</ul></div>'

    cards_html = "\n".join(cards)
    week_display = html.escape(week)

    return f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#1b1b1b">
<title>טרנדים ב-AI {week_display}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Hebrew:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg: #1b1b1b;
    --bg-elevated: #232323;
    --fg: #c5c1b9;
    --fg-strong: #dcdad5;
    --fg-muted: #a09d96;
    --fg-subtle: #96928c;
    --accent: #22c55e;
    --accent-glow: rgba(34,197,94,0.6);
    --accent-soft: rgba(34,197,94,0.12);
    --accent-softer: rgba(34,197,94,0.04);
    --accent-border: rgba(34,197,94,0.12);
    --accent-border-hover: rgba(34,197,94,0.3);
    --shadow-glow-md: 0 0 15px rgba(34,197,94,0.3), 0 0 40px rgba(34,197,94,0.1);
    --text-glow: 0 0 8px rgba(34,197,94,0.6), 0 0 20px rgba(34,197,94,0.3);
    --font-sans: 'Noto Sans Hebrew', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 16px;
    --radius-pill: 999px;
    --transition: 0.3s cubic-bezier(0.4,0,0.2,1);
    --transition-fast: 0.15s cubic-bezier(0.4,0,0.2,1);
  }}

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html {{ -webkit-text-size-adjust: 100%; }}

  body {{
    background: var(--bg);
    color: var(--fg);
    font-family: var(--font-sans);
    font-size: clamp(1rem, 2vw, 1.0625rem);
    line-height: 1.7;
    padding-top: env(safe-area-inset-top);
    padding-bottom: env(safe-area-inset-bottom);
  }}

  /* ── GRID BACKGROUND ── */
  body::before {{
    content: '';
    position: fixed;
    inset: 0;
    z-index: 0;
    pointer-events: none;
    background-image:
      linear-gradient(rgba(34,197,94,0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(34,197,94,0.03) 1px, transparent 1px);
    background-size: 40px 40px;
    mask-image: radial-gradient(ellipse 80% 60% at 50% 0%, black 40%, transparent 100%);
    -webkit-mask-image: radial-gradient(ellipse 80% 60% at 50% 0%, black 40%, transparent 100%);
  }}

  .wrap {{
    position: relative;
    z-index: 1;
    max-width: 720px;
    margin: 0 auto;
    padding: 24px 16px 80px;
  }}

  /* ── TOP BAR ── */
  .top-bar {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    gap: 10px;
  }}
  .lang-btn, .share-btn {{
    background: var(--accent-softer);
    border: 1px solid var(--accent-border);
    border-radius: var(--radius-pill);
    color: var(--accent);
    font-family: var(--font-sans);
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.5px;
    padding: 7px 16px;
    cursor: pointer;
    transition: all var(--transition-fast);
    display: flex;
    align-items: center;
    gap: 6px;
    min-height: 44px;
    -webkit-tap-highlight-color: transparent;
  }}
  .lang-btn:hover, .share-btn:hover {{
    background: var(--accent-soft);
    border-color: var(--accent);
    box-shadow: 0 0 10px var(--accent-glow);
  }}
  .share-btn svg {{ width: 16px; height: 16px; stroke: var(--accent); }}
  .share-btn.copied {{ background: var(--accent-soft); }}
  .share-copied {{
    font-size: 0.72rem;
    color: var(--accent);
    margin-top: 4px;
    text-align: center;
    opacity: 0;
    transition: opacity 0.3s;
  }}
  .share-copied.show {{ opacity: 1; }}

  /* ── HEADER ── */
  .site-header {{ margin-bottom: 24px; }}
  .header-eyebrow {{
    font-size: 0.8rem;
    font-weight: 500;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--accent);
    text-shadow: var(--text-glow);
    margin-bottom: 6px;
  }}
  .header-title {{
    font-size: clamp(1.6rem, 4vw, 2.2rem);
    font-weight: 700;
    color: var(--fg-strong);
    line-height: 1.3;
    text-shadow: 0 0 30px rgba(34,197,94,0.1);
    margin-bottom: 4px;
  }}
  .header-sub {{
    font-size: 0.875rem;
    color: var(--fg-muted);
    font-weight: 300;
  }}

  /* ── CUSTOM AUDIO PLAYER ── */
  .player {{
    position: sticky;
    top: 0;
    z-index: 10;
    background: rgba(27,27,27,0.92);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border-bottom: 1px solid var(--accent-border);
    padding: 12px 16px;
    margin: 0 -16px 24px;
  }}
  .player audio {{ display: none; }}

  .player-ui {{
    display: flex;
    align-items: center;
    gap: 12px;
  }}
  .player-btn {{
    flex-shrink: 0;
    width: 44px;
    height: 44px;
    border-radius: 50%;
    background: var(--accent);
    border: none;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all var(--transition-fast);
    box-shadow: 0 0 12px rgba(34,197,94,0.4);
  }}
  .player-btn:hover {{
    transform: scale(1.08);
    box-shadow: 0 0 20px rgba(34,197,94,0.6);
  }}
  .player-btn svg {{ width: 18px; height: 18px; fill: #0a1a0f; }}

  .player-center {{ flex: 1; min-width: 0; }}
  .player-track {{
    font-size: 0.8rem;
    font-weight: 500;
    color: var(--fg-strong);
    margin-bottom: 6px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}
  .player-progress-wrap {{
    position: relative;
    height: 4px;
    background: rgba(255,255,255,0.1);
    border-radius: 2px;
    cursor: pointer;
    overflow: hidden;
  }}
  .player-progress-bar {{
    height: 100%;
    width: 0%;
    background: var(--accent);
    border-radius: 2px;
    box-shadow: 0 0 6px var(--accent-glow);
    transition: width 0.1s linear;
    pointer-events: none;
  }}
  .player-progress-wrap:hover .player-progress-bar {{
    box-shadow: 0 0 12px var(--accent-glow);
  }}

  .player-time {{
    font-size: 0.72rem;
    color: var(--fg-subtle);
    white-space: nowrap;
    flex-shrink: 0;
    font-variant-numeric: tabular-nums;
    min-width: 70px;
    text-align: center;
  }}

  .player-hint {{
    font-size: 0.72rem;
    color: var(--fg-subtle);
    margin-top: 7px;
    letter-spacing: 0.3px;
  }}

  /* ── RUN NOTES ── */
  .run-notes {{
    background: var(--accent-softer);
    border: 1px solid var(--accent-border);
    border-right: 3px solid var(--accent);
    border-radius: var(--radius-md) 0 0 var(--radius-md);
    padding: 12px 16px;
    margin-bottom: 24px;
    font-size: 0.875rem;
    color: var(--fg-strong);
  }}
  [dir="ltr"] .run-notes {{
    border-right: 1px solid var(--accent-border);
    border-left: 3px solid var(--accent);
    border-radius: 0 var(--radius-md) var(--radius-md) 0;
  }}
  .run-notes ul {{ padding-right: 20px; margin-top: 6px; }}
  [dir="ltr"] .run-notes ul {{ padding-right: 0; padding-left: 20px; }}

  /* ── CARDS ── */
  .card {{
    position: relative;
    background: var(--accent-softer);
    border: 1px solid var(--accent-border);
    border-radius: var(--radius-lg);
    margin-bottom: 16px;
    transition: border-color var(--transition), background var(--transition), box-shadow var(--transition);
  }}
  .card:hover {{
    border-color: var(--accent-border-hover);
    background: rgba(34,197,94,0.07);
    box-shadow: var(--shadow-glow-md), 0 12px 32px rgba(0,0,0,0.25);
  }}

  .card__rank {{
    position: absolute;
    top: -1px;
    right: 20px;
    background: var(--accent);
    color: #0a1a0f;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.5px;
    padding: 3px 10px;
    border-radius: 0 0 var(--radius-sm) var(--radius-sm);
  }}
  [dir="ltr"] .card__rank {{ right: auto; left: 20px; }}

  .card__body {{ padding: 28px 20px 20px; }}

  /* card header: title block + star stat */
  .card__header {{
    display: flex;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 10px;
  }}
  .card__title-block {{ flex: 1; min-width: 0; }}
  .card__eyebrow {{
    font-size: 0.78rem;
    font-weight: 500;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: var(--accent);
    text-shadow: var(--text-glow);
    margin-bottom: 4px;
  }}
  .card__title {{
    font-size: 1.1rem;
    font-weight: 600;
    line-height: 1.35;
  }}
  .card__title a {{
    color: var(--fg-strong);
    text-decoration: none;
    transition: color var(--transition-fast);
    word-break: break-word;
  }}
  .card__title a:hover {{ color: var(--accent); }}
  .card__org {{
    color: var(--fg-muted);
    font-weight: 400;
  }}

  .card__stats {{
    flex-shrink: 0;
    text-align: center;
    background: var(--accent-soft);
    border: 1px solid var(--accent-border);
    border-radius: var(--radius-md);
    padding: 8px 12px;
    min-width: 56px;
  }}
  .card__stars {{
    color: #f0c674;
    font-size: 1.1rem;
    line-height: 1;
  }}
  .stars-num {{
    display: block;
    font-size: 0.85rem;
    font-weight: 700;
    color: var(--fg-strong);
    margin-top: 2px;
  }}

  .card__meta {{
    display: flex;
    flex-wrap: wrap;
    gap: 4px 14px;
    font-size: 0.78rem;
    color: var(--fg-subtle);
    margin-bottom: 10px;
  }}
  .meta-icon {{ opacity: 0.5; }}

  .card__tags {{
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 16px;
  }}
  .tag {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: var(--radius-pill);
    background: var(--accent-soft);
    border: 1px solid var(--accent-border);
    color: var(--accent);
    font-size: 0.72rem;
    font-weight: 500;
    letter-spacing: 0.3px;
    white-space: nowrap;
    transition: all var(--transition-fast);
  }}
  .tag:hover {{
    background: rgba(34,197,94,0.16);
    border-color: var(--accent);
    box-shadow: 0 0 10px var(--accent-glow);
  }}

  /* ── BRIEF SECTIONS ── */
  .card__content {{ display: flex; flex-direction: column; gap: 0; }}

  .brief-section {{
    padding: 10px 0;
    border-top: 1px solid var(--accent-border);
  }}
  .brief-section:first-child {{ border-top: none; padding-top: 0; }}

  .brief-label {{
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: var(--accent);
    text-shadow: var(--text-glow);
    margin-bottom: 4px;
  }}
  .brief-text {{
    font-size: 0.9375rem;
    color: var(--fg-muted);
    font-weight: 300;
    line-height: 1.7;
  }}

  /* "Why it matters" gets a highlight treatment */
  .brief-section--matters {{
    background: var(--accent-soft);
    border: 1px solid var(--accent-border);
    border-radius: var(--radius-md);
    padding: 10px 14px;
    margin-top: 8px;
  }}
  .brief-section--matters .brief-label {{ margin-bottom: 3px; }}
  .brief-section--matters .brief-text {{
    color: var(--fg-strong);
    font-weight: 400;
  }}

  .desc {{ font-size: 0.9375rem; color: var(--fg-muted); font-weight: 300; line-height: 1.7; }}
  .label {{ color: var(--accent); font-weight: 600; }}

  /* ── FOOTER ── */
  .site-footer {{
    margin-top: 40px;
    font-size: 0.78rem;
    color: var(--fg-subtle);
    text-align: center;
    border-top: 1px solid var(--accent-border);
    padding-top: 20px;
  }}
  a {{ color: var(--accent); }}

  /* ── MOBILE SAFETY ── */
  img, video, audio {{ max-width: 100%; }}
  .card__title a {{ word-break: break-word; }}
  @media (max-width: 480px) {{
    .card__body {{ padding: 28px 14px 16px; }}
    .card__stats {{ padding: 6px 10px; min-width: 50px; }}
    .player-time {{ display: none; }}
  }}
</style>
</head>
<body>
<div class="wrap">

  <div class="top-bar">
    <button class="lang-btn" id="langToggle" onclick="toggleLang()">EN</button>
    <button class="share-btn" id="shareBtn" onclick="shareReport()" aria-label="Share">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/>
        <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/>
        <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
      </svg>
      <span class="share-label i18n" data-he="שתף" data-en="Share">שתף</span>
    </button>
  </div>

  <header class="site-header">
    <p class="header-eyebrow i18n" data-he="עיכול AI שבועי" data-en="Weekly AI Digest">עיכול AI שבועי</p>
    <h1 class="header-title i18n" data-he="&#128293; טרנד ב-AI/LLM" data-en="&#128293; Trending AI/LLM Repos">&#128293; טרנד ב-AI/LLM</h1>
    <p class="header-sub">{week_display} &middot; {html.escape(generated_for)}</p>
  </header>

  <div class="player">
    <audio id="audio" src="report.mp3" preload="none"></audio>
    <div class="player-ui">
      <button class="player-btn" id="playBtn" onclick="togglePlay()" aria-label="Play">
        <svg id="iconPlay" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
        <svg id="iconPause" viewBox="0 0 24 24" style="display:none"><path d="M6 19h4V5H6zm8-14v14h4V5z"/></svg>
      </button>
      <div class="player-center">
        <div class="player-track i18n" data-he="&#127911; האזן בדרך לעבודה" data-en="&#127911; Listen on your commute">&#127911; האזן בדרך לעבודה</div>
        <div class="player-progress-wrap" id="progressWrap" onclick="seek(event)">
          <div class="player-progress-bar" id="progressBar"></div>
        </div>
      </div>
      <div class="player-time" id="playerTime">0:00 / 0:00</div>
    </div>
    <p class="player-hint i18n" data-he="לחץ להפעלה · גלול למטה לקריאה" data-en="Tap to play · scroll to read">לחץ להפעלה · גלול למטה לקריאה</p>
  </div>

  {warn_html}

  <main id="repoList">
{cards_html}
  </main>

  <footer class="site-footer">
    <span class="i18n" data-he="עיכול אוטומטי שבועי · מקור: GitHub Search API" data-en="Auto-generated weekly digest · Data: GitHub Search API">עיכול אוטומטי שבועי · מקור: GitHub Search API</span>
    <p class="share-copied" id="shareCopied">&#128279; <span class="i18n" data-he="הקישור הועתק!" data-en="Link copied!">הקישור הועתק!</span></p>
  </footer>

</div>

<script>
// ── LANGUAGE TOGGLE ──
var currentLang = 'he';
function toggleLang() {{
  currentLang = currentLang === 'he' ? 'en' : 'he';
  var isHe = currentLang === 'he';
  document.documentElement.lang = currentLang;
  document.documentElement.dir = isHe ? 'rtl' : 'ltr';
  document.getElementById('langToggle').textContent = isHe ? 'EN' : 'עב';
  document.querySelectorAll('.i18n').forEach(function(el) {{
    el.innerHTML = el.dataset[currentLang] || el.innerHTML;
  }});
  // Flip brief labels
  document.querySelectorAll('.brief-label').forEach(function(el) {{
    var he = el.dataset.he, en = el.dataset.en;
    if (he && en) el.textContent = isHe ? he : en;
  }});
}}

// ── SHARE ──
function shareReport() {{
  var title = currentLang === 'he'
    ? 'טרנד ב-AI/LLM – {week_display}'
    : 'Trending AI/LLM Repos – {week_display}';
  var url = window.location.href;
  if (navigator.share) {{
    navigator.share({{ title: title, url: url }}).catch(function(){{}});
  }} else {{
    navigator.clipboard.writeText(url).then(function() {{
      var el = document.getElementById('shareCopied');
      el.classList.add('show');
      setTimeout(function() {{ el.classList.remove('show'); }}, 2500);
    }}).catch(function() {{
      prompt('Copy this link:', url);
    }});
  }}
}}

// ── AUDIO PLAYER ──
var audio = document.getElementById('audio');
var playBtn = document.getElementById('playBtn');
var iconPlay = document.getElementById('iconPlay');
var iconPause = document.getElementById('iconPause');
var progressBar = document.getElementById('progressBar');
var progressWrap = document.getElementById('progressWrap');
var playerTime = document.getElementById('playerTime');

function fmt(s) {{
  s = Math.floor(s || 0);
  return Math.floor(s/60) + ':' + ('0' + (s%60)).slice(-2);
}}
function updateTime() {{
  var cur = audio.currentTime, dur = audio.duration;
  progressBar.style.width = (dur ? (cur/dur*100) : 0) + '%';
  playerTime.textContent = fmt(cur) + ' / ' + fmt(dur);
}}
function togglePlay() {{
  if (audio.paused) {{ audio.play(); }} else {{ audio.pause(); }}
}}
audio.addEventListener('play', function() {{
  iconPlay.style.display = 'none';
  iconPause.style.display = 'block';
}});
audio.addEventListener('pause', function() {{
  iconPlay.style.display = 'block';
  iconPause.style.display = 'none';
}});
audio.addEventListener('ended', function() {{
  iconPlay.style.display = 'block';
  iconPause.style.display = 'none';
  progressBar.style.width = '0%';
}});
audio.addEventListener('timeupdate', updateTime);
audio.addEventListener('loadedmetadata', updateTime);
function seek(e) {{
  if (!audio.duration) return;
  var rect = progressWrap.getBoundingClientRect();
  var frac = (e.clientX - rect.left) / rect.width;
  audio.currentTime = Math.max(0, Math.min(1, frac)) * audio.duration;
}}
</script>
</body>
</html>
"""


# Label translations for brief sections injected by the runner
BRIEF_LABELS = {
    "What it does":         {"he": "מה זה עושה",       "en": "What it does"},
    "Why it's trending":    {"he": "למה זה בטרנד",     "en": "Why it's trending"},
    "Example use case":     {"he": "דוגמת שימוש",       "en": "Example use case"},
    "Why it matters for you": {"he": "למה זה רלוונטי לך", "en": "Why it matters for you"},
}


def wrap_brief_section(label_en, text, is_matters=False):
    """Return a structured brief-section div with bilingual label."""
    labels = BRIEF_LABELS.get(label_en, {"he": label_en, "en": label_en})
    cls = "brief-section brief-section--matters" if is_matters else "brief-section"
    return (
        f'<div class="{cls}">'
        f'<p class="brief-label" data-he="{html.escape(labels["he"])}" '
        f'data-en="{html.escape(labels["en"])}">'
        f'{html.escape(labels["he"])}</p>'
        f'<p class="brief-text">{text}</p>'
        f'</div>'
    )


def render_narration(data):
    week = data.get("week", "")
    repos = data.get("repos", [])
    spoken_week = week.replace("-W", ", week ") if week else week
    lines = [
        f"Your trending A.I. repos digest for {spoken_week}.",
        f"Here are the {len(repos)} most relevant new repositories this week.",
        "",
    ]
    for i, r in enumerate(repos, 1):
        name = r.get("full_name", "")
        spoken_name = name.replace("/", ", by ").replace("-", " ")
        lang = r.get("language") or "unknown language"
        stars = r.get("stars", 0)
        desc = (r.get("description") or "").strip().rstrip(".")
        narr = r.get("narration")
        if narr:
            lines.append(f"Number {i}. {narr}")
        else:
            lines.append(
                f"Number {i}. {spoken_name}. Written in {lang}, "
                f"with {stars:,} stars. {desc}."
            )
        lines.append("")
    lines.append("That's your weekly AI digest. Have a great week.")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="infile", default="-")
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()

    raw = (
        sys.stdin.read()
        if args.infile == "-"
        else open(args.infile, encoding="utf-8").read()
    )
    data = json.loads(raw)

    os.makedirs(args.outdir, exist_ok=True)
    with open(os.path.join(args.outdir, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(render_html(data))
    with open(os.path.join(args.outdir, "narration.txt"), "w", encoding="utf-8") as fh:
        fh.write(render_narration(data))
    print(f"wrote {args.outdir}/index.html and narration.txt for {data.get('week')}")


if __name__ == "__main__":
    main()
