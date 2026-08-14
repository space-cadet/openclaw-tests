# token-usage — Skill Card

| Field | Value |
|-------|-------|
| **Name** | token-usage |
| **Version** | v2.4.0 |
| **One-liner** | Track, aggregate, and report OpenClaw token usage and costs across sessions. |

## Trigger
- "How many tokens did I use today/this week/past 24 hours?"
- "What's my session cost?"
- Budget monitoring or anomaly detection

## Architecture

**Two approaches:**

1. **Direct Parser (`parse.py`)** — Recommended for cron jobs. No database setup. Reads session JSONL directly. Supports rolling time windows (`--hours`, `--since`, `--until`).
2. **SQLite Database (`ingest.py` + `report.py`)** — Optional. Incremental ingestion, long-term retention, SQL queries.

## Key Commands

### Direct Parser (Recommended)
```bash
# Past N hours (rolling window)
cd scripts && python3 parse.py --hours 24 --by-model --costs

# Since a specific time
cd scripts && python3 parse.py --since "2026-07-20T09:00:00" --by-model --costs

# Relative time shorthand
cd scripts && python3 parse.py --since 2d --by-model --costs
cd scripts && python3 parse.py --since 30m --by-model --costs

# Yesterday's usage (ideal for daily cron)
cd scripts && python3 parse.py --yesterday --costs

# Today's usage
cd scripts && python3 parse.py --today --costs

# Last N days
cd scripts && python3 parse.py --days 3 --by-model --costs

# Weekly usage
cd scripts && python3 parse.py --week --costs

# All time by model
cd scripts && python3 parse.py --all --by-model --costs

# By cron job
cd scripts && python3 parse.py --week --by-cron --costs

# Include cache columns
cd scripts && python3 parse.py --today --cache --costs

# Per-session detail
cd scripts && python3 parse.py --today --session-detail --costs

# JSON output
cd scripts && python3 parse.py --week --json
```

### SQLite Database (Optional)
```bash
# Initialize database (one-time)
cd scripts && python3 ingest.py --init

# Daily incremental ingestion
cd scripts && python3 ingest.py

# Reports
cd scripts && python3 report.py --yesterday --compact
cd scripts && python3 report.py --week --compact
cd scripts && python3 report.py --month --compact
```

## New in v2.4.0

| Change | Description |
|--------|-------------|
| Shared parser | OpenClaw messages and Codex rollouts use one parser. |
| Provider support | Kimi, OpenAI/GPT, Claude, and OpenRouter model names are handled. |
| Cache reporting | Cached tokens appear separately in direct and SQLite reports. |
| Local dates | UTC timestamps are grouped by the local timezone. |
| Tests | OpenClaw, Codex, gzip, midnight, and SQLite comparison tests are included. |

## Earlier changes

| Fix | Description |
|-----|-------------|
| Timezone-aware daily reports | `--today` and `--yesterday` now use local timezone (Asia/Calcutta / IST) instead of UTC. Fixes daily cron reports at 04:00 IST showing wrong day. |
| Model alias mapping | Unprefixed model names (e.g., `k3`) are auto-mapped to full form (`kimi/k3`) for pricing lookup. |
| K3 pricing | Added `k3` entry to `pricing.json` alongside existing `kimi/k3`. |
| Missing file resilience | Parser gracefully skips deleted/missing session files instead of crashing. |

## New in v2.2.0

| Feature | Flag | Description |
|---------|------|-------------|
| Multi-source pricing | `update-pricing.py` | Fetches Kimi direct + OpenRouter pricing |
| Dreaming token tracking | `parse.py --all` | Parses dreaming session files for total usage |

## New in v2.1.0

| Feature | Flag | Description |
|---------|------|-------------|
| Rolling windows | `--hours N` | Last N hours (e.g., `--hours 24`) |
| Arbitrary ranges | `--since`, `--until` | ISO timestamps, dates, or relative (`2d`, `1h`, `30m`) |
| Day ranges | `--days N` | Last N calendar days |
| Cache tracking | `--cache` | Include cacheRead/cacheWrite columns |
| Session detail | `--session-detail` | Per-session breakdown with models |
| Performance | mtime filtering | Skips unmodified files when `--since` is used (critical for 7000+ files) |

## Cron Jobs (Direct Parser — Recommended)

| Job | Schedule | Command | Purpose |
|-----|----------|---------|---------|
| Daily Report | 04:00 local | `parse.py --yesterday --costs` | Yesterday's usage by model |
| Weekly Report | Monday 09:00 | `parse.py --week --costs` | 7-day trend + cost |

## Cron Jobs (SQLite — Optional)

| Job | Schedule | Command | Purpose |
|-----|----------|---------|---------|
| Daily Ingest | 04:00 local | `ingest.py` | Incremental ingestion |
| Daily Report | 09:05 local | `report.py --yesterday --compact` | SQLite report |
| Monthly Rotation | 1st 00:05 | `ingest.py --rotate` | Roll up 90+ day data |

## Job Type Classification

- `user` — Interactive sessions
- `cron:<name>` — Cron-triggered sessions (auto-detected)
- `background` — Background tasks

## Dependencies
- Python 3
- OpenClaw session JSONL files in `~/.openclaw/agents/*/sessions/`
- `scripts/pricing.json` (user-editable)
- SQLite3 (for SQLite database only)

## Quick Example

```bash
cd skills/token-usage/scripts
python3 parse.py --hours 24 --by-model --costs
```

Output:
```
## Past 24 Hours (2026-07-20 10:15 → 2026-07-21 10:15 UTC)
  kimi/k3                     in=  152,834  out=  12,419  msgs=  42
                              est. $0.1013
  kimi/k2.7                   in=  893,221  out=  78,432  msgs= 156
                              est. $0.6035
  kimi/k2.7-code              in=   12,445  out=     892  msgs=   3
                              est. $0.0080
  Period total                in=1,058,500  out=  91,743  msgs= 201
                                est. $0.7128
```

> Important: The system sums `input + output` tokens only. `totalTokens` includes `cacheRead` which would overcount if summed across messages.

## Session File Management

With 7000+ session files, reports can slow down. Tips:
- Use `--since` / `--hours` — mtime filtering skips unmodified files automatically
- Compress old sessions: `find *.jsonl -mtime +30 -exec gzip {} \;`
- The parser handles `.jsonl.gz` transparently

## Retention (SQLite only)
- Daily: 90 days → rolled to monthly
- Monthly: Kept forever
