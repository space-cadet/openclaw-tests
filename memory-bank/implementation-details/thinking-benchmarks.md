# Thinking Level Benchmark Methodology

**Related task:** T14 — OpenAI Luna Thinking Level Benchmark  
**Created:** 2026-09-02

---

## Why This Benchmark Exists

The `thinking` parameter on OpenAI's newer models (gpt-5.6-luna, gpt-5.6-sol, gpt-5.6-terra) controls reasoning effort. But "reasoning" is vague. This benchmark measures **what actually changes** across levels: correctness, depth, token usage, and self-corrections.

## Design Principles

1. **Tasks have known traps** — The naive approach is wrong. Deeper reasoning catches it.
2. **Scoring is granular** — Not just pass/fail. 100-point rubrics with 4 dimensions.
3. **Blind evaluation** — I score outputs without knowing which thinking level produced them.
4. **Same prompt, same model** — Only thinking level varies.

## Task Selection Rationale

| Task | What it tests |
|------|--------------|
| T1 (geometric series) | Baseline — does the model work at all? |
| T2 (pivot force) | **Constraint awareness** — energy conservation is necessary but not sufficient |
| T3 (Markov chain) | **Counterintuitive asymmetry** — symmetry arguments fail |
| T4 (async bug) | **Execution tracing** — requires simulating state over time |
| T5 (Ramsey planner) | **Long-horizon planning** — recognizes when generic solutions fail |

## Scoring Philosophy

- **40% answer**: Did they get the right number? This is table stakes.
- **30% approach**: Did they use the right method? Separates lucky guesses from understanding.
- **20% trap**: Did they explicitly discuss why the naive approach fails? This is the "reasoning" we care about.
- **10% clean**: Is the derivation rigorous? Catches hand-waving.

## Why Native Codex?

OpenRouter does not expose thinking level controls. The native Codex app-server does. This benchmark routes through `provider: openai` with `api: openai-responses` — the same path as the Codex CLI.

## Known Limitations

- **Single model** — Only gpt-5.6-luna. Sol/Terra have different reasoning ranges.
- **No repetition** — One run per level per task. No variance estimate.
- **Subjective scoring** — My judgment on "identifies the trap" is not objective.
- **Context window** — Small tasks (< 500 tokens). Long-context reasoning is not tested.

## Future Work

- Add Sol and Terra comparisons
- Repeat runs for variance
- Automate scoring (pattern matching on key phrases)
- Add long-context tasks (multi-step proofs, document analysis)
