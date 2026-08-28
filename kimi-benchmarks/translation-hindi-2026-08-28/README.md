# Hindi Translation Benchmark — CJP Website

**Date:** 2026-08-28
**Model:** kimi/k2.7
**Task:** English → Hindi translation of educational civics content (HTML)
**Tester:** Cloudy (via OpenClaw subagent spawn)

## Summary

Translation of 512KB educational content across 21 Politics module pages.
Average throughput: **73 tokens/second**, **~5 minutes per page**.
Context overflow observed with 4-page batches; 3-page batches are safe.

## Key Findings

| Metric | Value |
|--------|-------|
| Average token rate | 73 t/s |
| Tokens per page (avg) | ~22K |
| Time per page (avg) | ~5 min |
| Context limit observed | ~3.4M prompt/cache |
| Safe batch size | ≤3 pages |
| Overflow batch size | 4 pages (39m, no output) |

## Files

- [`results.md`](results.md) — Detailed per-batch measurements
- [`methodology.md`](methodology.md) — Measurement approach and caveats
- [`recommendations.md`](recommendations.md) — Batch sizing and prompt optimization

## Raw Data

All measurements from OpenClaw subagent runs with `model=kimi/k2.7`.
Token counts from subagent completion events (reported by OpenClaw runtime).

