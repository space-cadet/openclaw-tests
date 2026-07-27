# Active Context: openclaw-tools

## Current Status: Token-Usage v2.3.0 Published (2026-07-27)

### What Just Happened (2026-07-28)
- **Imported mem-* skills from Deepak's `.agents/skills/`**: `mem-update`, `mem-scan`, `mem-format`, `mem-load`
  - Adapted for Sage's workspace with **project-repo awareness** (Step 0)
  - **Problem fixed**: `mb-text-workflow` lacked project-repo awareness, causing T35c to be created in workspace instead of timesarrow repo
  - **Solution**: `mem-update` Step 0 scans ALL repos before creating tasks, preventing duplicate/wrong-location entries
  - **Sanitized**: Removed `/Users/deepak/` and `/Users/sage/` paths, replaced with `~/` and `${MB_CORE_PATH}`
  - **Skills added to repo**: `mem-format`, `mem-load`, `mem-scan`, `mem-update`
  - **Registry updated**: `skills-registry.json` now includes all 4 new skills (25 total)
  - **Committed**: Pending push

### Previous Major Work (2026-07-27)
- **Fixed timezone bug**: `--today`/`--yesterday` now use local timezone (Asia/Calcutta/IST) instead of UTC
  - Root cause: Daily cron at 04:00 IST was computing "yesterday" in UTC, getting wrong day
  - Fix: Added `zoneinfo.ZoneInfo("Asia/Calcutta")` to parse.py date boundary calculation
- **Fixed K3 pricing**: Session files store `"model":"k3"` but pricing.json only had `"kimi/k3"`
  - Fix: Added `"k3"` entry to pricing.json + alias fallback in `estimate_cost()`
- **Added missing file resilience**: Parser now skips deleted session files gracefully
- **ClawHub published**: token-usage@2.3.0 (k97d6heqfp7013mg1qvq4hq3ss8b8w8s)
- **Committed**: `5a3e1c3` on main

### Previous Major Work (2026-07-23)
- **Built `update-pricing.py`**: Multi-source pricing fetcher for model cost tracking
  - Fetches **342 models** from OpenRouter API (`/api/v1/models`)
  - Scrapes **Moonshot direct pricing** from official docs (CNY→USD at ~7.2 rate)
  - Creates `registry.json` with model metadata: availability, provider, context windows, alternative pricing
  - Compares sources: OpenRouter vs direct (e.g., K3: $2.78/M vs $3.00/M — ~8% markup)
- **Fixed `parse.py` bug**: None cache pricing caused TypeError in cost estimation
- **Updated weekly cron**: Token Usage — Weekly Report now refreshes pricing before generating report
- **ClawHub published**: v2.2.4 live (latest tag, 307 downloads) — multi-source pricing with OpenRouter + Moonshot direct
- **Committed**: `37f65af` on main

### Previous Major Work (2026-07-21)
- **Documented `agent-knowledge` ClawHub skill**: Created `skills/knowledge/SKILL.md` with usage docs, data model, and QMD integration
- **Updated README.md**: Added `knowledge` *(ClawHub)* to the skills index under Memory & Knowledge Management

### Previous Major Work (2026-07-20)
- **Created `cron-management` skill** — CLI tool for managing OpenClaw cron jobs

### Next Focus
- T2: Benchmark verification (tests moved, not yet verified post-move)
- T5: Token usage tracking — Phase 6: ClawHub publish with pricing features

### Open Questions
- Should tests/ have their own memory-bank or use repo-level one?
- GitHub Actions CI — worth it for a tools repo?
