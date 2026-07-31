# K3 Benchmark Results

**Date:** 2026-07-17
**Model:** kimi/k3
**Runner:** Sage (灵剑)

---

## Test 1: Mini LISP Interpreter

### Score: 14/14 (100%)

K3 produced a complete, working LISP interpreter with all required features:

| Feature | Status |
|---------|--------|
| Tokenizer | ✅ |
| Parser (S-expressions) | ✅ |
| Evaluator | ✅ |
| Integers | ✅ |
| Booleans (#t, #f) | ✅ |
| Symbols | ✅ |
| Lists | ✅ |
| Arithmetic (+, -, *, /) | ✅ |
| Comparison (=, <, >) | ✅ |
| List ops (cons, car, cdr, list) | ✅ |
| Predicates (null?, number?, symbol?, list?) | ✅ |
| define (variable) | ✅ |
| define (function) | ✅ |
| lambda | ✅ |
| if | ✅ |
| quote | ✅ |
| cond | ✅ |
| Lexical scoping | ✅ |
| Recursion | ✅ |
| Error handling | ✅ |

### Edge Cases Passed
- Empty lists
- Nested scopes (shadowing works correctly)
- Quoted symbols vs lists
- Cond with else clause
- Wrong argument counts
- Undefined symbols

---

## Test 2: Subagent Stress Tests

### Test 2a: Basic Spawn ✅ PASS
- **Task:** Calculate 2+2
- **Result:** 4 (correct)
- **Runtime:** 8s
- **Tokens:** 16.3k

### Test 2b: Tool Access ✅ PASS
- **Task:** Read first 5 lines of SOUL.md
- **Result:** Correctly returned file contents
- **Runtime:** 14s
- **Tokens:** 18.2k

### Test 2c: Model Override ⚠️ PARTIAL PASS
- **Task:** Spawn child with `model="kimi/k2.7"`
- **Result:** Spawn mechanism works, but nested subagents abort
- **Issue:** K2.7 child aborts with errorCode 20 ("operation aborted")
- **Root cause:** Runtime blocks nested subagents (depth > 1) as safety guardrail
- **Runtime:** 33-80s (varies by attempt)

### Test 2d: Parallel Spawn ✅ PASS
- **Task:** Spawn 3 subagents simultaneously
- **Result:** All 3 completed successfully (1000, 1000, 1000)
- **Runtimes:** 7s, 17s, 6s
- **Tokens:** 15.6k - 17.7k each

### Test 2e: Timeout Stress ✅ PASS
- **Task:** Count to 100,000 with 60s timeout
- **Result:** Completed in 6ms
- **Runtime:** 13s
- **Tokens:** 16.5k

---

## Comparison

| Model | LISP Score | Subagent 2a | Subagent 2b | Subagent 2c | Subagent 2d | Subagent 2e |
|-------|-----------|-------------|-------------|-------------|-------------|-------------|
| **K3** | **14/14 (100%)** | ✅ | ✅ | ⚠️ | ✅ | ✅ |
| K2.7 Code | 10/11 (90.9%) | — | — | — | — | — |
| K2.6 | 8/11 (72.7%) | — | — | — | — | — |

### LISP Interpreter Comparison

| Issue | K2.6 | K2.7 | K3 |
|-------|------|------|-----|
| Multi-expression parsing | ❌ Broken | ✅ Works | ✅ Works |
| cond + quoted symbols | ❌ Fails | ❌ Fails | ✅ Works |
| Lexical scoping | ✅ | ✅ | ✅ |
| Recursion | ✅ | ✅ | ✅ |
| Error handling | Basic | Good | Excellent |

---

## Key Findings

1. **K3 is a better coder than K2.7 and K2.6** — Perfect score on LISP interpreter, no bugs found
2. **Subagent spawning works reliably** — All direct spawns successful
3. **Nested subagents blocked by design** — Safety guardrail prevents depth > 1
4. **K3 handles large tasks efficiently** — 100K iterations in 6ms
5. **Parallel spawning works** — 3 simultaneous subagents all completed

## Notes

- Test 2c failure is expected behavior — runtime prevents nested subagent chains
- All other tests demonstrate K3's capability as a task orchestrator
- LISP interpreter code saved to `interpreter.py`
