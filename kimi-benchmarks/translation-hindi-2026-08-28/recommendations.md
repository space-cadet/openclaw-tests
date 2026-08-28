# Recommendations — Hindi Translation

## Batch Sizing

| Scenario | Recommended Batch | Rationale |
|----------|-------------------|-----------|
| Routine translation | 3 pages | Safe, reliable, ~15 min |
| Large pages (>30KB) | 2 pages | Prevents context pressure |
| Quick test/verification | 1 page | Fastest feedback loop |
| Production throughput | 3-page parallel | Two subagents = ~30 min for 6 pages |

**Never use 4-page batches** with current prompt overhead. Context overflow risk is high.

## Prompt Optimization

### Current (bloated)
- Full 8-point guidelines repeated every batch
- Self-review checklist (8 items)
- Multiple examples and edge cases
- **Overhead: ~4K tokens per batch**

### Recommended (trimmed)
- Single reference to established guidelines ("Follow CJP translation standards")
- No self-review checklist (trust model quality or verify externally)
- No redundant examples
- **Target overhead: ~1K tokens per batch**

### Minimal (for speed)
- Page list only
- Single line: "Translate to Hindi, formal educational tone, preserve HTML"
- **Overhead: ~200 tokens**

## Cost Estimation

For remaining 97 Hindi stubs (~24KB avg):

| Approach | Batches | Time | Est. Tokens |
|----------|---------|------|-------------|
| 1-page sequential | 97 | ~8 hours | ~2.1M |
| 2-page sequential | 49 | ~8 hours | ~2.1M |
| 3-page sequential | 33 | ~8 hours | ~2.1M |
| 3-page parallel (2x) | 17 rounds | ~4 hours | ~2.1M |

**Note:** Parallel 2x halves wall time but doesn't reduce total token cost.

## Model Selection

| Model | Best For | Avoid |
|-------|----------|-------|
| k2.7 | Multi-page batches, reliable | Single-page (overkill) |
| K3 | Single-page precision | Multi-page (overflow risk) |
| k2.7-code | Not tested | — |

## Quality vs. Speed Tradeoffs

1. **Fastest:** Minimal prompt, 3-page batches, no self-review
   - Risk: More errors, requires external review
   
2. **Balanced:** Trimmed prompt, 3-page batches, spot-check 20%
   - Good for production pace
   
3. **Thorough:** Full guidelines, 2-page batches, 100% review
   - Best for high-stakes content (Constitution, Judiciary)

## Context Management

To reduce context pressure:
1. Trim prompts after first batch (guidelines established)
2. Don't carry previous translations in context (start fresh subagent per batch)
3. Split large pages (>35KB) into smaller batches
4. Avoid parallel subagents on same module (context collision risk)

## File Organization

Benchmark data should follow:
```
kimi-benchmarks/
  translation-hindi-YYYY-MM-DD/
    README.md         # Summary and navigation
    results.md        # Tables with raw measurements
    methodology.md    # How measurements were taken
    recommendations.md # Actionable guidance
```

See [context-degradation/](../context-degradation/) for another example.

