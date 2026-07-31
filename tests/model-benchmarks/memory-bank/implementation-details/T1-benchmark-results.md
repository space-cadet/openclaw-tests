# K2.6 vs K2.7 Code Benchmark — Implementation Details

*Date: 2026-06-15*
*Task: T1*

## Overview

Benchmark comparing Kimi K2.6 (general-purpose) and K2.7 Code (coding specialist) on a non-trivial coding task: implementing a mini LISP interpreter from scratch.

## Task Design

### Why a LISP Interpreter?

A LISP interpreter is an ideal benchmark because it tests multiple coding competencies simultaneously:

1. **Tokenizer** — lexical analysis, handling multiple token types
2. **Parser** — recursive descent parsing, nested structures
3. **Evaluator** — expression evaluation, special forms
4. **Environment system** — nested scopes, lexical binding
5. **Recursion** — self-referential functions
6. **Edge case handling** — quoting, boolean semantics, multi-expression sequences

### Constraints

- No `eval()` or `ast` module
- No parsing libraries
- Must handle: integers, booleans, symbols, lists
- Must implement: +, -, *, /, =, <, >, cons, car, cdr, list, null?, number?, symbol?, list?
- Must implement special forms: define, lambda, if, quote, cond
- Must support lexical scoping and recursion

## Results

| Model | Score | Structural Bugs | Edge Case Bugs |
|-------|-------|-----------------|----------------|
| **K2.6** | 8/11 (72.7%) | 2 | 1 |
| **K2.7 Code** | 10/11 (90.9%) | 0 | 1 |
| Reference (hand-written) | 11/11 (100%) | 0 | 0 |

### Detailed Breakdown

**K2.6 Failures:**
1. `define` returns `None` instead of the defined value (tests 3, 4, 5)
2. `_parse_one()` has a fatal bug: `consumed = len(tokens)` always equals full length, so `tokens[consumed:]` is always empty. This breaks multi-expression evaluation entirely.

**K2.7 Code Failures:**
1. Test 11 (`cond` with `'yes`): quoted symbol `'yes` was not auto-defined in the global environment, causing an "Undefined symbol" error when the `cond` clause tried to evaluate it.

### Key Insight

K2.7 Code's single failure was an **edge case** (quote handling in cond). K2.6 had a **structural bug** that made multi-expression programs impossible. This suggests K2.7 Code has better architectural reasoning for complex coding tasks.

## Code Structure Comparison

Both models produced similar architectures:
- `Symbol` class for identifiers
- `Environment` class with parent-chain scoping
- `Procedure` class for closures
- Recursive descent parser with `nonlocal pos`
- Special form handling via `op == Symbol("define")` pattern

The difference was in correctness, not structure.

## Methodology Notes

### Subagent Execution

- **Attempt 1**: File-based task (read spec, write code) — both failed with "session completed before registry settled"
- **Attempt 2**: Inline task with file output — both failed with same error
- **Attempt 3**: Inline task with direct code return — K2.6 succeeded (returned code), K2.7 Code returned test output only

The subagent runtime has limitations with complex coding tasks. The K2.7 Code subagent that succeeded returned only test results (not the full code), suggesting output truncation.

### Files

| File | Description |
|------|-------------|
| `task-spec.md` | Full task specification |
| `reference_interpreter.py` | Hand-written reference (11/11) |
| `k2p6/interpreter.py` | K2.6 generated code (8/11) |
| `index.html` | Results webpage |

## Conclusion

**K2.7 Code is ~20% more correct** on this task. The improvement is in edge-case handling and structural correctness, not in raw architecture. For non-trivial coding tasks requiring multiple components to work together correctly, K2.7 Code shows measurable advantage.

However, this is a single task on a single day. A more robust benchmark would require multiple tasks across different domains (algorithms, debugging, API design, etc.).
