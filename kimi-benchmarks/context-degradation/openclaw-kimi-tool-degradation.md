# OpenClaw/Kimi Long-Context Tool Degradation

**Date recorded:** 2026-08-23
**Task:** T13
**Scope:** Two independent OpenClaw clients, called Instance A and Instance B

## Summary

Both instances showed the same practical failure during long Telegram sessions:
at roughly 130k reported context, tool calls stopped producing usable results,
while ordinary text conversation continued. The failure persisted across turns
and recovered after a session reset or gateway cycle.

This is a confirmed operational symptom. The exact mechanism is not proven.
The leading explanation is Telegram delivery-copy messages inflating the model
history, possibly interacting with Kimi tool-call or replay handling.

## Observed facts

- The failure was repeatable and persistent in both instances.
- Text generation continued beyond 150k reported context.
- Tools failed silently rather than returning a useful error.
- Context readings changed without a corresponding recorded compaction:
  approximately 144k to 95k, and later 155k to 153k and back toward 155k.
- The failing session was explicitly using `kimi/k3`, reporting about 153k
  tokens against a 1,048,576-token context window.
- Kimi requests immediately examined returned HTTP 200; no matching 429 or
  ordinary network failure was found.

## OpenClaw evidence

- The Gateway WebSocket limit found in the installed source was 25 MB, with a
  larger outbound-buffer limit. No generic 130k WebSocket or IPC limit was
  found.
- OpenClaw repeatedly logged live tool-result truncation: 64,000 characters
  per result and 256,000 characters in aggregate. This can prune prompt
  material without incrementing `compactionCount`.
- A separate 256 KiB serialized trajectory-event limit affected diagnostic
  persistence. It is not, by itself, evidence that the live prompt was cut at
  that size.
- Replay normalization and the saved session showed no duplicate internal
  message IDs or obviously broken tool-call/result pairs.

## Telegram delivery-copy finding

The persisted session contained ordinary assistant replies and separate
Telegram delivery-mirror assistant rows with identical text but different
record IDs:

- 20 delivery-mirror rows were found.
- 19 duplicate assistant-text groups were identified.
- Mirror text totalled about 26,808 characters, 48.6% of all assistant text in
  the session examined.
- The model-history path inspected did not appear to filter these mirror rows
  before constructing later prompts.

This confirms a context-inflation mechanism. It does not yet prove that the
mirrors alone caused tool failure.

## What remains uncertain

The evidence does not distinguish conclusively among:

1. Telegram delivery mirrors consuming too much effective Kimi history;
2. Kimi tool-call or streaming behavior failing at a lower practical context
   boundary than the advertised model window;
3. an OpenClaw replay, truncation, or recovery interaction triggered by the
   enlarged history; or
4. a transport/serialization limit outside the Gateway WebSocket path.

The exact hardcoded 130k transport constant proposed earlier was not found.
The simple K2.7 model-mismatch explanation was also not supported by the
failing session, which reported K3 with a 1M context profile.

## Next investigations

- Compare a long-lived Telegram session with an equivalent non-Telegram
  OpenClaw surface.
- Exclude delivery-mirror rows from model history in a controlled build or
  diagnostic harness, then compare the last successful and first failed tool
  calls.
- Correlate prompt assembly, truncation, replay, compaction, and provider
  request events around the first failure.
- Preserve model, effective context window, context reading, tool outcome,
  provider status, and reset outcome in a sanitized event record.
- Prepare an upstream OpenClaw issue only after the mirror-exclusion comparison.

## Related work

- T7: `kimi-benchmarks/k3/results.md` — ordinary K3 capability baseline.
- T11: `memory-bank/implementation-details/model-availability-study.md` —
  direct versus OpenClaw measurement design.
- T12: `memory-bank/implementation-details/kimi-retry-monitor.md` — Kimi
  retry and HTTP 429 diagnostics.
