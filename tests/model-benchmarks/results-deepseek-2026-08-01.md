# Benchmark Results: DeepSeek v4 vs Kimi K3

*Date: 2026-08-01*
*Task: Mini LISP Interpreter*
*Tester: Sage (灵剑) via OpenClaw*

## Task Description

Build a minimal LISP interpreter in Python supporting:
- Data types: integers, booleans (#t/#f), symbols, lists
- Built-ins: +, -, *, /, =, <, >, cons, car, cdr, list, null?, number?, symbol?, list?
- Special forms: define, lambda, if, quote, cond
- Requirements: lexical scoping, recursion, no eval()/ast, meaningful errors

## Results Summary

| Model | Provider | Score | Runtime | Self-Correction | Extra Tests |
|-------|----------|-------|---------|-----------------|-------------|
| **Kimi K3** | Kimi | **14/14 (100%)** | ~2 min | N/A (first pass) | 0 |
| **DeepSeek v4-Pro** | DeepSeek | **25/25 (100%)** | ~2.5 min | Minor (quote token fix) | 11 |
| **DeepSeek v4-Flash** | DeepSeek | **16/16 (100%)** | ~5 min | **Major** (4→0 failures) | 2 |

## Detailed Results

### Kimi K3 (Baseline)
- **File**: `k3/interpreter.py`
- **Lines**: ~370
- **Tests**: 14 (all from spec)
- **Failures**: 0
- **Notes**: Clean, minimal implementation. Passed all tests on first attempt.

### DeepSeek v4-Pro
- **File**: `deepseek-v4-pro/interpreter.py`
- **Lines**: 565
- **Tests**: 25 (14 from spec + 11 extra)
- **Failures**: 0
- **Extra tests added**:
  - Type predicates: `number?`, `null?`, `list?`, `symbol?`
  - Complex nested: `(double (add 3 4))`
  - Arity edge cases: `car` too few/too many args
  - Cond with variable: `(cond ((> x 5) 'big) (else 'small))`
  - Letter grade function using cond
- **Self-correction**: Fixed quote tokenization bug during development
- **Notes**: Most thorough implementation. Added comprehensive test coverage beyond spec.

### DeepSeek v4-Flash
- **File**: `deepseek-v4-flash/interpreter.py`
- **Lines**: ~480
- **Tests**: 16 (14 from spec + 2 extra)
- **Initial failures**: 4 (cons representation, quote evaluation, quote shorthand, arity check)
- **Final result**: 16/16 after self-correction
- **Self-correction details**:
  - Fixed "Not a proper list" cons bug
  - Fixed quote TypeError (evaluator tried to call quoted list)
  - Fixed quote shorthand returning Symbol objects
  - Added missing arity check for built-ins
- **Notes**: Took ~5 minutes to debug and fix. Shows strong iterative improvement capability.

## Key Observations

1. **v4-Pro is competitive with K3** on coding tasks. It produced more thorough test coverage and handled edge cases well.

2. **v4-Flash self-corrects effectively** — initial failures were all fixed during the session without human intervention.

3. **v4-Pro added 11 extra tests** unprompted, showing stronger initiative on completeness.

4. **All models passed** — the benchmark may be too easy to distinguish top-tier models. Consider harder tasks (e.g., parser with precedence climbing, state machine, concurrency).

## File Locations

- `k3/interpreter.py` — Kimi K3 implementation
- `deepseek-v4-pro/interpreter.py` — DeepSeek V4 Pro implementation
- `deepseek-v4-flash/interpreter.py` — DeepSeek V4 Flash implementation
- `task-spec.md` — Benchmark specification

## Recommendations

- **v4-Pro**: Use for complex coding tasks requiring thoroughness and edge-case handling
- **v4-Flash**: Use for routine tasks where speed matters; budget extra time for self-correction
- **K3**: Still excellent baseline; fastest first-pass success rate

---
*Benchmark run via OpenClaw subagent spawn. All implementations written from scratch by respective models.*
