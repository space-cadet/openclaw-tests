---
name: token-usage
description: "Track, aggregate, and report OpenClaw token usage and costs across sessions."
homepage: https://github.com/space-cadet/openclaw-tools/tree/main/skills/token-usage
license: MIT
version: "2.3.0"
---

# Token Usage Tracker

Parse OpenClaw session JSONL files to extract token usage, aggregate by date/model/session, and generate cost reports.

## When to Use

- User asks "how many tokens did I use today/this week"
- User wants to know session costs or model breakdown
- Budget monitoring and anomaly detection
- Before/after optimization comparisons

## Workflow

1. **Locate sessions** — Find `.jsonl` files in `~/.openclaw/agents/*/sessions/`
2. **Parse usage** — Extract `input`, `output`, `cacheRead`, `cacheWrite`, `totalTokens` from each assistant message
3. **Aggregate** — Group by date, model, session ID
4. **Report** — Output summaries, trends, cost estimates

## Commands

### Time Period Selection

| Flag | Description | Example |
|------|-------------|---------|
| `--today` | Current calendar day (local timezone) | `--today` |
| `--yesterday` | Previous calendar day (local timezone) | `--yesterday` |
| `--week` | Last 7 calendar days | `--week` |
| `--days N` | Last N calendar days | `--days 3` |
| `--hours N` | Rolling window: last N hours | `--hours 24` |
| `--since TIME` | Start time (ISO, date, or relative) | `--since 24h`, `--since 2d`, `--since "2026-07-20T09:00:00"` |
| `--until TIME` | End time (ISO, date, or relative) | `--until 1h` |
| `--all` | All time | `--all` |

**Relative time shorthand:** `1h` = 1 hour ago, `2d` = 2 days ago, `30m` = 30 minutes ago.

### Report by Model (with costs)
```bash
# Past 24 hours, model breakdown with cost estimates
python3 ~/.openclaw/skills/token-usage/scripts/parse.py --hours 24 --by-model --costs

# Today so far
python3 ~/.openclaw/skills/token-usage/scripts/parse.py --today --by-model --costs

# Yesterday
python3 ~/.openclaw/skills/token-usage/scripts/parse.py --yesterday --by-model --costs

# Since a specific time
python3 ~/.openclaw/skills/token-usage/scripts/parse.py --since "2026-07-20T09:00:00" --by-model --costs

# Last 2 hours
python3 ~/.openclaw/skills/token-usage/scripts/parse.py --since 2h --by-model --costs
```

### Report by Cron Job (daily breakdown per job)
```bash
python3 ~/.openclaw/skills/token-usage/scripts/parse.py --week --by-cron
```

### All-time summary by model
```bash
python3 ~/.openclaw/skills/token-usage/scripts/parse.py --all --by-model
```

### Export to JSON for external dashboards
```bash
python3 ~/.openclaw/skills/token-usage/scripts/parse.py --week --json > /tmp/token-report.json
```

### Additional Output Options

| Flag | Description |
|------|-------------|
| `--cache` | Include cache read/write columns in report |
| `--session-detail` | Show per-session breakdown with models used |
| `--json` | Output machine-readable JSON |
| `--costs` | Add cost estimates (requires pricing data) |

## Timezone Behavior

`--today` and `--yesterday` use the **local system timezone** (Asia/Calcutta / IST by default). This ensures daily reports align with your local day even when cron jobs run at off-UTC hours (e.g., 04:00 IST = 22:30 UTC previous day).

## Model Aliases

Session files may store model names in short form (`k3`, `k2.7`) or long form (`kimi/k3`). The parser normalizes these for pricing lookup:
- Short form (`k3`) → tries `k3` then `kimi/k3`
- Full form (`kimi/k3`) → direct lookup

Sessions are stored as JSONL with lines like:
```json
{"type":"message","message":{"role":"assistant",...},"usage":{"input":1000,"output":500,"totalTokens":1500},...}
```

## Cost Estimation

Uses model pricing from `scripts/pricing.json` (user-editable). Default prices:
- Kimi k2.7: $0.90/1M input, $3.75/1M output
- Kimi k3: $2.78/1M input, $13.89/1M output
- Kimi k2.7-code: $0.90/1M input, $3.75/1M output
- Claude Sonnet 4: $3.00/1M input, $15.00/1M output
- GPT-4o: $2.50/1M input, $10.00/1M output

Costs are approximate. Cache read/write pricing applied when available. Unprefixed model names (e.g. `k3`) are automatically mapped to their full form (`kimi/k3`) for pricing lookup.

## Session File Management

Session files accumulate over time. The `~/.openclaw/agents/main/sessions/` directory can grow to several GB with thousands of files, slowing down reports.

**Current usage check:**
```bash
# Total size and file count
du -sh ~/.openclaw/agents/main/sessions/
ls ~/.openclaw/agents/main/sessions/*.jsonl | wc -l

# Size by month (to identify heavy periods)
ls -l ~/.openclaw/agents/main/sessions/*.jsonl | awk '
  {month = substr($6, 1, 3); year = $8; size += $5; count++}
  END {printf "Total: %.2f MB across %d files\n", size/1024/1024, count}'
```

**Archiving old sessions:**
```bash
# Compress sessions older than 30 days (preserves access, saves ~80% space)
find ~/.openclaw/agents/main/sessions/*.jsonl -mtime +30 -exec gzip {} \;

# Move very old sessions to archive (after verifying no longer needed)
mkdir -p ~/.openclaw/agents/main/sessions/archive
find ~/.openclaw/agents/main/sessions/*.jsonl -mtime +90 -exec mv {} ~/.openclaw/agents/main/sessions/archive/ \;
```

**Note:** The parser already skips `.trajectory.jsonl` and temp files, and uses mtime filtering to skip unmodified files when `--since` is specified.

## Important: What "Total" Means

The script reports **input + output tokens** as the usage metric. This is the actual new token consumption per turn.

The `totalTokens` field in session files includes `cacheRead` (cached context window), which gets re-counted at every turn. Summing `totalTokens` across messages would massively overcount — a 10K context used for 100 turns would appear as 1M tokens. The script avoids this by only summing `input` and `output`.

## Output Locations

- Daily summaries: `~/.openclaw/skills/token-usage/logs/YYYY-MM-DD.md`
- Weekly reports: `~/.openclaw/skills/token-usage/logs/week-YYYY-Www.md`
- Raw JSON exports: user-specified or `/tmp/token-usage-*.json`

## Limitations

- Only parses assistant messages with `usage` fields (OpenClaw 2026.5+ format)
- Historical sessions before JSONL format not supported
- Costs are estimates; actual billing may differ
- With many session files (7000+), first run may take 10-30 seconds; subsequent runs with `--since` are fast due to mtime filtering
