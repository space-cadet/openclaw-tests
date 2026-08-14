---
source_branch: main
source_commit: d386a35
---
#### 18:24:00 IST - T10: Fix local dates, CLI windows, and report cache totals
- Modified `skills/token-usage/scripts/common.py` - Added local timestamp and date helpers.
- Modified `skills/token-usage/scripts/parse.py` - Added rolling-window flags and local-day grouping.
- Modified `skills/token-usage/scripts/ingest.py` - Store SQLite dates in local time.
- Modified `skills/token-usage/scripts/report.py` - Show cache totals and use local time.
- Modified `tests/token_usage/test_parsers.py` - Added gzip and midnight-boundary coverage.
- Modified `memory-bank/tasks/T10.md` - Recorded completed work.
- Modified `memory-bank/implementation-details/token-usage.md` - Updated remaining work.
- Modified `memory-bank/session_cache.md` - Updated T10 progress.
