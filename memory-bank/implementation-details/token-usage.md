# Token Usage Tracking

*Last Updated: 2026-08-14 17:35:37 IST*

## Current Design

The skill has two paths:

- `parse.py` reads session files directly.
- `ingest.py` copies totals into SQLite, and `report.py` reads the database.

These paths repeat the same work. This is the main source of drift.

## Known Gaps

- The SQLite importer only reads OpenClaw message records.
- Codex rollout records are not yet imported into SQLite.
- Unknown models can still receive Kimi pricing in the importer.
- Cache tokens are stored in some places but are not always included in cost totals.
- The cron report assumes Kimi pricing.
- Model aliases are not handled in one shared place.
- The docs list flags that the current direct parser does not provide.
- UTC timestamps are not always converted to the local day before grouping.
- There are no parser tests with small sample files.
- The checked-in database can become stale.

## Planned Shape

Create one parser module that returns a common record:

- timestamp
- local date
- provider
- model
- input tokens
- output tokens
- cached input tokens
- cached write tokens
- session file

Both direct reports and SQLite ingestion should use these records. Unknown prices should be shown as unknown, not guessed.

## Simple Validation Plan

Use small fixtures for:

1. An OpenClaw message file.
2. A Codex rollout file.
3. A gzip file.
4. A cache hit.
5. A message just before and after midnight in India.
6. Short and full model names.

Compare direct and SQLite totals for every fixture.

## Work Done 2026-08-14

- Added `common.py` for shared parsing, model aliases, and cost lookup.
- Connected `parse.py` and `ingest.py` to the shared parser.
- Added tests for an OpenClaw record and a Codex record.
- Confirmed the earlier Luna session still totals 214,888 new tokens.

The main code block is ready for v2.4.0. ClawHub publishing remains after final review.
