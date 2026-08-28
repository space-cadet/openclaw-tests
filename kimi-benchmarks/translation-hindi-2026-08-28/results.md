# Detailed Results — Hindi Translation Benchmark

## Per-Batch Measurements

| Batch | Module | Pages | Runtime | In Tokens | Out Tokens | Rate (t/s) | Status |
|-------|--------|-------|---------|-----------|------------|------------|--------|
| 1 | Constitution | 4 | 20m38s | ~73K | ~20K | 75 | ✅ Complete |
| 2 | Constitution | 4 | ~22m | — | — | — | ✅ Complete |
| 3 | Constitution | 4 | 29m45s | 71.8K | 36.2K | 60 | ✅ Complete |
| 4 | Constitution | 4 | 23m23s | 77K | 33K | 78 | ✅ Complete |
| 5 | Personalities | 4 | 39m32s | 3.4M prompt/cache | 0 | 0 | ❌ Overflow |
| 6 | Politics | 4 | 18m49s | 154K | 48K | 80 | ✅ Complete |
| 7 | Personalities | 3 | — | — | — | — | ⏳ Running |
| 8 | Politics | 3 | — | — | — | — | ⏳ Running |
| Single | Constitution | 1 | 5m12s | 25.1K | 7.1K | 103 | ✅ Complete (K3) |

**Average k2.7 rate (excluding overflow): 73 t/s**

## Token Breakdown Per Page

| Component | Tokens | Notes |
|-----------|--------|-------|
| Source HTML (24KB avg) | 8–12K | HTML tags are token-heavy |
| Hindi output | 10–15K | Hindi slightly more verbose than English |
| Reasoning/self-review | 2–4K | Varies by content complexity |
| **Total per page** | **~22K** | |

## Time Estimates

| Batch Size | Total Tokens | Estimated Time | Risk |
|------------|--------------|----------------|------|
| 1 page | 22K | ~5 min | None |
| 2 pages | 44K | ~10 min | Low |
| 3 pages | 66K | ~15 min | Safe |
| 4 pages | 88K | ~20 min | Overflow risk |

## Context Accumulation

k2.7 carries previous pages' content in context. By page 4:
- Previous pages: ~60K tokens
- Current page: ~22K tokens
- Prompt overhead: ~4K tokens
- **Total context: ~86K** (well below 3M limit, but effective working memory degrades)

The Batch 5 overflow at 3.4M prompt/cache after 39 minutes suggests either:
1. Repeated self-review iterations consuming tokens
2. Inefficient context management (carrying full page content unnecessarily)
3. Model-specific behavior at high context volumes

## File Sizes (Politics Module)

| Page | Size | Tokens (est.) |
|------|------|---------------|
| environmentalism.html | 25KB | ~8K |
| utilitarianism.html | 26KB | ~9K |
| ambedkar.html | 27KB | ~9K |
| gandhi.html | 28KB | ~9K |
| social-contract-theory.html | 37KB | ~12K |
| **Average** | **24KB** | **~8K** |

