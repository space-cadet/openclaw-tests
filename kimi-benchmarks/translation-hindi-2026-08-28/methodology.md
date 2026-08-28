# Methodology — Hindi Translation Benchmark

## Measurement Approach

### Setup
- **Repository:** `space-cadet/cjp-website`
- **Model:** kimi/k2.7 (via OpenClaw subagent spawn)
- **Content:** Educational civics pages in HTML format
- **Target language:** Hindi (formal educational register)

### Token Counting
- Source: OpenClaw subagent completion events
- `in` tokens: Input prompt + source content
- `out` tokens: Generated Hindi translation + reasoning
- `prompt/cache`: Accumulated context across the session
- Reported by OpenClaw runtime, not independently verified

### Timing
- Runtime: Wall-clock time from spawn to completion event
- Includes: reading source, translation, self-review, file I/O, git operations
- Not pure translation time — includes model reasoning overhead

### Content Characteristics
- HTML with SSI includes (`<!--#include virtual="..." -->`)
- Average page: ~24KB source
- Dense educational prose with technical terminology
- Mixed: constitutional articles, political philosophy, historical figures

### Caveats

1. **Self-review overhead:** Early batches included explicit self-review checklists (8 items). This added ~3-4K tokens per batch in prompt overhead but may have reduced error rates.

2. **HTML preservation:** Translation requires preserving all HTML tags, attributes, and SSI directives. This constrains output format and may increase token count vs. plain text.

3. **Context accumulation:** k2.7 retains previous pages in context within a subagent session. This causes effective memory pressure even though the raw token count is below the theoretical limit.

4. **Model version drift:** "k2.7" is a moving target. Benchmarks from 2026-08-28 may not apply to future versions.

5. **No control for prompt quality:** Later batches used trimmed prompts (removed redundant guidelines). This confounds batch size with prompt size.

## Reproducibility

To reproduce:
```bash
cd code/cjp-website
# Select any untranslated page
# Spawn subagent with model=kimi/k2.7
# Measure: runtime, in tokens, out tokens
```

Raw completion events stored in OpenClaw session logs (not committed to repo).

