# Weekly Trending AI/LLM Repos Brief — Design

**Date:** 2026-06-04
**Status:** Approved, pending implementation
**Owner:** Avi Levi

## Goal

A once-a-week automation that finds the week's trending AI/LLM GitHub repositories and writes a brief about each one into the Obsidian vault. The brief is grounded in real repo content (metadata + README), not guessed, and ties each repo to Avi's AI / L&D / content work where relevant.

## Summary of decisions

| Decision | Choice |
|---|---|
| Topic scope | AI / LLM / agents / ML focused |
| Output | Obsidian vault note under `Researches/Trending Repos/` |
| Brief depth | Standard brief + concrete example use case |
| Trigger | Claude scheduled routine calling a reusable skill |
| Volume | Top 10 repos |
| File organization | One dated note per week |
| First run | Immediately (manual run now) |
| Recurring run | Every Friday 16:00, starting the following Friday |

## Architecture

Two pieces with a clean split of responsibility:

1. **Skill `trending-ai-repos`** — contains all the logic: fetch trending AI/LLM repos, ground each in its README/metadata, write the weekly note. Runnable manually (`/trending-ai-repos`) and by the scheduler. Single source of truth for behavior.
2. **Scheduled routine** — a thin trigger that calls the skill every Friday at 16:00. Holds no logic of its own, so editing behavior only ever means editing the skill.

This separation means the manual run and the scheduled run always do exactly the same thing.

## Data flow

```
trigger (manual now / Friday 16:00)
  -> GitHub Search API: repos pushed in last 7 days, sorted by stars desc,
     filtered to AI/LLM signals (topics + name/description keywords)
  -> relevance filter + dedup -> top 10
  -> for each repo: fetch metadata + README excerpt
  -> cross-week dedup: read recent notes in the folder, flag repeats
  -> compose standard brief + concrete example use case per repo
  -> write note: Researches/Trending Repos/YYYY-Www Trending AI Repos.md
```

### Source of repos

- **Primary:** GitHub Search API. Query repos `pushed:>=<7 days ago>`, `sort=stars`, `order=desc`, scoped to AI/LLM signals:
  - Topics: `llm`, `agents`, `ai-agents`, `rag`, `machine-learning`, `generative-ai`, `llmops`, `mcp`, `prompt-engineering`.
  - Keyword match in name/description for AI/LLM terms.
- **Relevance filter:** drop results that are clearly not AI/LLM despite matching a broad term.
- **Top 10** after dedup.
- **Fallback:** if the API returns too few AI/LLM repos (< 10 usable), scrape `github.com/trending` (weekly window) and filter to AI/LLM, merging with API results.

### Cross-week dedup

Before writing, read the most recent 2-3 notes in `Researches/Trending Repos/`. A repo that appeared recently is not silently dropped — if it is genuinely still surging it stays, but is flagged `still trending`. This keeps each week's note fresh rather than repetitive.

## Output format

**Path:** `Researches/Trending Repos/YYYY-Www Trending AI Repos.md` (e.g. `2026-W23 Trending AI Repos.md`).

**Frontmatter:**
```yaml
---
created: YYYY-MM-DD
week: YYYY-Www
tags: [trending-repos, ai, llm, research]
type: weekly-digest
---
```

**Body:**
- A 1-2 line intro summarizing the week's theme.
- Ten repo briefs, each containing:
  - **Header:** repo name (linked to GitHub) + primary language + topic tags
  - **Stats:** total stars, stars gained this week (approx), last push date
  - **Summary:** 2-3 sentences on what it does (grounded in README/metadata)
  - **Why it's trending / who it's for**
  - **Example use case:** a concrete, specific scenario showing how Avi could use it, tied to his AI / L&D / content / Poalim work where it fits; a neutral general example when it genuinely does not relate to his work
  - **Why it matters for you:** a short tie-in note

## Per-repo brief template

```markdown
## [<repo-name>](<github-url>) — `<language>`
`<topic-tag>` `<topic-tag>` `<topic-tag>`

**Stats:** ⭐ <total> (+<gained this week> this week) · last push <date>

**What it does:** <2-3 sentences>

**Why it's trending:** <who it's for and why now>

**Example use case:** <concrete scenario tied to Avi's work where it fits>

**Why it matters for you:** <short tie-in>
```

## Failure handling

Never a silent failure. The note is always created, even on a partial run.

- Too few AI/LLM repos from the API -> trending-page fallback.
- README unfetchable for a repo -> still write its brief from metadata (thinner), note the gap.
- Any partial run -> a short note at the top of the file stating what was missing.

## Constraints and notes

- **Excludes `the-system-v8/`** by design — this automation only ever touches `Researches/Trending Repos/`.
- **Remote scheduling caveat:** the scheduled routine must be able to reach this working directory to write to the vault. This is verified at setup. If the remote routine cannot reach the local vault, the fallback is the manual-run skill plus a recurring calendar reminder, or emailing the digest. Confirmed during the scheduling step.
- GitHub Search API is used unauthenticated for light weekly use; if rate limits bite, an optional token can be added later (not required for v1).

## Out of scope (YAGNI for v1)

- Multi-source aggregation (Hacker News, Product Hunt).
- Code snippets per repo (decision was concrete scenario only).
- Email/Slack delivery (vault note only).
- A rolling single-file format (one dated note per week chosen instead).

## Rollout

1. Build the `trending-ai-repos` skill.
2. Run it once now to generate the `2026-W23` note.
3. Register the weekly Friday 16:00 scheduled routine, starting the following Friday.
