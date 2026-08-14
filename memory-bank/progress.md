# Progress: openclaw-tools Reorganization

## In Progress (2026-08-14)

### T10: Token-usage consistency across providers
- Audited the direct parser, SQLite importer, reports, pricing updater, and docs.
- Found that direct parsing and SQLite ingestion do not support the same session formats.
- Recorded the plan in `tasks/T10.md` and `implementation-details/token-usage.md`.
- Next: build one shared parser and add small tests.

### T10 update (2026-08-14)
- Added `skills/token-usage/scripts/common.py`.
- Connected the direct parser and SQLite importer to it.
- Added two parser tests.
- Remaining work: timezone boundaries, CLI flags, cron pricing, and full SQLite checks.

### T10 release (2026-08-14)
- Completed the v2.4.0 code block: shared parsing, Codex SQLite support, local dates, rolling windows, cache-aware reports, safe pricing, and comparison tests.
- Pushed commit `0371753`.
- ClawHub accepted v2.4.0 for publication. It is pending review; latest remains 2.3.0 until the review finishes.

## Completed (2026-07-27)

### Token-Usage v2.3.0: Timezone Fix, K3 Pricing, Model Aliases
- **Fixed timezone bug**: `--today`/`--yesterday` now use local timezone (Asia/Calcutta/IST)
  - Root cause: 04:00 IST cron was computing "yesterday" in UTC, showing wrong day
  - Fix: `zoneinfo.ZoneInfo("Asia/Calcutta")` in parse.py date boundaries
- **Fixed K3 pricing**: Added `"k3"` entry to pricing.json + alias fallback in `estimate_cost()`
  - Session files store short model names (`k3`) but pricing had only full names (`kimi/k3`)
- **Missing file resilience**: Parser skips deleted session files gracefully
- **Updated docs**: SKILL.md timezone behavior + model alias sections; skill-card.md v2.3.0 changelog
- **ClawHub published**: token-usage@2.3.0
- **Commit**: `5a3e1c3`

## Completed (2026-07-23)

### Token-Usage v2.2.0: Multi-Source Pricing & Model Registry
- **Created `update-pricing.py`** — multi-source pricing fetcher
  - OpenRouter API: 342 models with per-token pricing
  - Moonshot direct: scraped from platform.kimi.com/docs/pricing/, CNY→USD conversion
  - Output: `pricing.json` + `registry.json` with metadata
  - Price comparison: OpenRouter markup vs direct (K3: +8%, K2.7-code: +9%, K2.6: -24%)
- **Fixed `parse.py`**: None cache pricing TypeError bug
- **Updated weekly cron**: pricing refresh runs before report generation
- **ClawHub published**: v2.2.4 live (latest tag, 307 downloads)
- **Commit**: `37f65af`

## Completed (2026-07-21)

### Token-Usage v2.1.0 Update
- Enhanced `skills/token-usage/scripts/parse.py` with rolling time windows
  - `--hours N` — rolling N-hour window
  - `--since` / `--until` — ISO timestamps, dates, or relative (`1d`, `2h`, `30m`)
  - `--days N` — last N calendar days
  - `--yesterday` — single calendar day
  - `--cache` — include cache read/write columns
  - `--session-detail` — per-session breakdown with models
  - Mtime filtering for performance (skips unmodified files)
- Updated `SKILL.md` with v2.1.0 documentation
- Updated `skills-registry.json` — token-usage version 2.1.0
- Commits: `7bc7ede`, `88cc111`

### Knowledge Skill Documentation
- Documented `agent-knowledge` ClawHub skill in repo
- Created `skills/knowledge/SKILL.md` with usage, data model, QMD integration docs
- Updated `README.md` skills index
- Audit: 5 ClawHub skills installed, all now documented
- Commit: `61a8ded`

## Completed (2026-07-20)

### Cron Management Skill (T8)
- Created `skills/cron-management/` with SKILL.md, skill-card.md, _meta.json
- Created `scripts/cronctl.sh` — CLI for listing, pausing, resuming, maintenance mode
- Tested all commands: list, status, pause, resume, pause-all, resume-all, maintenance, health
- Updated skills-registry.json
- Commit: `a1d3b8f`

### T1: Repo Infrastructure ✅
- Renamed from openclaw-tests
- Memory-bank v6.12 set up
- README.md, CONTRIBUTING.md, .gitignore all written

### T3: Skills Migration ✅
- **20 skills** in repo, all sanitized
- 10 original + 4 from workspace (graph-memory, netstatus, protonvpn-openvpn, worker-safety) + 2 custom (openclaw-backup, openclaw-backup-optimized)
- All have SKILL.md + skill-card.md + _meta.json
- skills-registry.json created for machine-readable index

### T4: Scripts Migration ✅
- **6 scripts** migrated with environment-based configuration
- check-disk.sh, crash-recovery.sh, heartbeat-watchdog.sh, netstatus.sh, protonvpn.sh, security-update-check.sh
- All use env vars for paths, no hardcoded personal references

### T6: Documentation ✅
- README.md with full skills index
- CONTRIBUTING.md with sanitization checklist
- .gitignore covering Node, Python, workspace artifacts, secrets
- 18 skill-card.md files for quick reference

## In Progress
- T2: Benchmark verification (tests moved, not yet verified)

## Not Started
- GitHub Actions CI (optional)

## Completed (2026-07-20)
- **T8: Cron Management Skill**
  - 21st skill added to repo
  - Solves the "no simple toggle" problem for OpenClaw cron jobs
  - Maintenance mode flag works even when OpenClaw is down

## Completed (2026-07-17)
- **T7: K3 Benchmark**
  - LISP interpreter: 14/14 (100%) — perfect score, no bugs
  - Subagent tests: 4/5 PASS, 1 PARTIAL (nested subagents blocked by design)
  - K3 outperforms K2.7 Code (10/11) and K2.6 (8/11)
  - Results saved to `tests/kimi-benchmarks/k3/`

## Completed (2026-07-16)
- **T5 Phase 5: parse.py Enhancement**
  - Added `--yesterday` flag to `parse.py` (+5 lines)
  - Updated `SKILL.md` — documented both direct parser (recommended) and SQLite (optional) approaches
  - Updated `skill-card.md` to v1.2.0 with new commands and examples
  - Workspace cron jobs switched to `parse.py` (accurate, no DB overhead)
  - SQLite tools (`ingest.py`, `report.py`) remain available for advanced use cases

## Completed (2026-07-15)
- T5: Token Usage Tracking System — SQLite database, incremental ingestion, 4 cron jobs, rotation
  - 6589 session files ingested on initialization
  - Daily ingest + report, weekly report, monthly rotation
  - 90-day daily retention, monthly summaries forever

## Metrics
- Skills: 21 (+ knowledge, + cron-management)
- Scripts: 7 (+ cronctl.sh)
- Tests: 2 suites (kimi-benchmarks, subagent-tests)
- Lines of documentation: ~3200 (README + CONTRIBUTING + skill-cards)
