# Model Benchmark: K2.6 vs K2.7 Code

## Task: Mini LISP Interpreter

Build a minimal LISP interpreter in Python supporting:

### Data Types
- Integers (e.g., `42`, `-3`)
- Booleans (`#t`, `#f`)
- Symbols (e.g., `x`, `factorial`, `+`)
- Lists (e.g., `(1 2 3)`, `(a b c)`)

### Built-in Functions
- Arithmetic: `+`, `-`, `*`, `/` (integer division)
- Comparison: `=`, `<`, `>`
- List: `cons`, `car`, `cdr`, `list`
- Predicates: `null?`, `number?`, `symbol?`, `list?`

### Special Forms
- `(define name value)` — define global variable
- `(define (name args...) body)` — define function
- `(lambda (args...) body)` — anonymous function
- `(if condition then-expr else-expr)` — conditional
- `(quote expr)` — return expr unevaluated
- `(cond (test expr)... [(else expr)])` — multi-branch conditional

### Requirements
1. Write tokenizer, parser, and evaluator from scratch
2. No `eval()`, `ast` module, or parsing libraries
3. Must handle nested scopes (lexical scoping)
4. Must handle recursion correctly
5. Must detect and report meaningful errors

### Test Cases (must all pass)
```python
# Basic arithmetic
(+ 1 2) => 3
(* (+ 1 2) (- 5 2)) => 9

# Variables and functions
(define x 10)
(+ x 5) => 15

(define (factorial n)
  (if (= n 0)
      1
      (* n (factorial (- n 1)))))
(factorial 5) => 120

# Lambda
(define square (lambda (x) (* x x)))
(square 7) => 49

# Lists
(cons 1 (cons 2 (cons 3 '()))) => (1 2 3)
(car (list 1 2 3)) => 1
(cdr (list 1 2 3)) => (2 3)

# Quoting
(quote (+ 1 2)) => (+ 1 2)
(quote (a b c)) => (a b c)

# Nested scopes
(define x 5)
(define (foo x) (+ x 10))
(foo 3) => 13
x => 5  # x should still be 5 globally

# Cond
(cond ((> 5 3) 'yes) (else 'no)) => yes

# Error handling
(factorial) => Error: too few arguments
(undefined 1) => Error: undefined symbol
```

### Output Format
Write complete Python code in `interpreter.py`. Include a `run_tests()` function that runs all test cases and prints pass/fail. Also print the number of passing tests and total tests.

### Scoring
- Correctness: all tests pass
- Code quality: clean, readable, well-structured
- Error handling: meaningful error messages
- Edge cases: empty lists, undefined symbols, wrong arg counts
