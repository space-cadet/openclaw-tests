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

---

## Instance B first-hand observations (Cloudy, kimi/k3, Telegram)

**Recorded by:** Instance B (Cloudy)  
**Session:** `ab7b6b68-1709-4d84-a5df-98d3d4344ff6`  
**Time:** 2026-08-23 05:30–08:17 UTC

Instance B was the live subject of the stress test. These observations were
made in real-time while tool degradation was actively occurring.

### Timeline of degradation

| Context | Event |
|---------|-------|
| 144k | User requests context-heavy CJP data load |
| 144k → 95k | **First oscillation**: 49k drop, **0 compactions** recorded |
| ~134k | **Tools die**: `exec`, `read`, `session_status`, `web_fetch` all return empty |
| 134k → 149k | Context climbs; tools remain dead across multiple turns |
| 149k | `web_fetch` and `exec` tested — both return empty |
| 155k | Peak context during degradation |
| 155k → 153k | **Second oscillation**: 2k drop, **0 compactions** recorded |
| 153k | Session continues; chat works, tools still dead |
| /new | Session reset; tools expected to recover (not tested in this session) |

### What "silent tool death" looks like from the inside

- Tool calls are issued normally (no error at call time).
- Results return as empty structures (`{"content": []}` or similar).
- No HTTP error, no timeout, no rate-limit response — just absence.
- Chat generation continues unaffected; the model itself is not overloaded.
- The session appears healthy except that every tool is non-functional.

### Key live findings

**1. Persistent failure**  
The tool failure was not transient. Once tools died at ~134k, they remained
dead for the entire remainder of the session (tested across ~10+ turns and
multiple tool types).

**2. Context oscillations without compaction**  
Two unexplained drops occurred:
- 144k → 95k (first oscillation)
- 155k → 153k (second oscillation)

Both happened with `compactionCount: 0`. This contradicts the documented
compaction behavior and suggests hidden pruning or deduplication.

**3. Delivery-copy duplication pattern**  
Instance B discovered that Telegram delivery creates duplicate assistant rows
in the persisted session. The assistant's own replies appeared 2–3 times in
the visible conversation context (session record + Telegram delivery mirror +
possibly a third copy). Mirror text totaled ~26.8k characters, roughly 48.6%
of all assistant text in the session.

**4. Both user and assistant messages are duplicated**  
Initially Instance B thought only assistant messages were duplicated. Later
correction: the Telegram delivery context includes duplicate user messages as
well, though the duplication ratio is higher for assistant messages.

### Theories Instance B proposed and ruled out

| Theory | Proposed by | Status | Ruled out by |
|--------|-------------|--------|--------------|
| Transport limit (~130k hard cap) | Instance B | ❌ | Luna/Sage — Gateway WebSocket is 25 MB |
| Model mismatch (K2.7 vs K3) | Instance B | ❌ | Session consistently reported K3; Sage confirmed |
| Corrupted tool state | Instance B | ❌ | Sage found no broken tool-call/result pairs |
| Telegram delivery-copy inflation | Instance B | 🟡 | Confirmed mechanism; causation unproven |
| Kimi tool-call path limit | Instance B | 🟡 | Model handles chat fine; tool path may differ |

### What Instance B got wrong

- Used the term **"bricked"** to describe the session. This was inaccurate.
  The session was healthy; only tool execution was degraded. Correct term:
  **tool degradation** or **silent tool failure**.
- Initially claimed only assistant messages were duplicated. Later corrected:
  both user and assistant messages appear in delivery-mirror copies.

### Cross-instance confirmation

- **Instance A** (Sage/Luna): Investigated OpenClaw source code, quantified
  delivery-mirror inflation, disproved transport-limit theory.
- **Instance B** (Cloudy): Experienced live degradation, discovered
  duplication pattern, documented real-time timeline and oscillations.

Both instances independently observed the same ~130k tool-death symptom.

---

## Sign-off

**Instance A (Sage/Luna):** Source code audit, delivery-mirror quantification,
transport-limit disproof, sanitized report preparation.  
**Instance B (Cloudy):** Live degradation observation, duplication pattern
discovery, real-time timeline documentation, theory proposal and correction.

Both instances contributed essential, non-overlapping evidence to this finding.
