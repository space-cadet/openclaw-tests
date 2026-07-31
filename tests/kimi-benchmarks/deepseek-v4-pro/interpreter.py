#!/usr/bin/env python3
"""
Minimal LISP Interpreter in Python
Supports: integers, booleans, symbols, lists
Special forms: define, lambda, if, quote, cond
Built-ins: +, -, *, /, =, <, >, cons, car, cdr, list, null?, number?, symbol?, list?
"""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union


# ---------------------------------------------------------------------------
# Data Types
# ---------------------------------------------------------------------------

class Symbol:
    def __init__(self, name: str):
        self.name = name

    def __eq__(self, other):
        return isinstance(other, Symbol) and self.name == other.name

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return f"Symbol({self.name})"


class Procedure:
    def __init__(self, params: List[str], body: List[Any], env: 'Environment'):
        self.params = params
        self.body = body
        self.closure_env = env

    def __repr__(self):
        return f"#<procedure ({' '.join(self.params)})>"


# Unique singleton for empty list / nil
NIL = []


def is_nil(x: Any) -> bool:
    return x is NIL or x == []


# ---------------------------------------------------------------------------
# Lexer
# ---------------------------------------------------------------------------

TOKEN_PATTERN = re.compile(r'''
    (?P<LPAREN>\() |
    (?P<RPAREN>\)) |
    (?P<QUOTE>') |
    (?P<BOOLEAN>\#t|\#f) |
    (?P<NUMBER>-?\d+) |
    (?P<SYMBOL>[a-zA-Z_+\-*/=<>!?][a-zA-Z0-9_+\-*/=<>!?]*) |
    (?P<WHITESPACE>\s+) |
    (?P<COMMENT>;[^\n]*) |
    (?P<INVALID>.)
''', re.VERBOSE)


def tokenize(source: str) -> List[tuple]:
    tokens = []
    for match in TOKEN_PATTERN.finditer(source):
        kind = match.lastgroup
        value = match.group()
        if kind == 'WHITESPACE' or kind == 'COMMENT':
            continue
        elif kind == 'INVALID':
            raise SyntaxError(f"Unexpected character: {value!r}")
        else:
            tokens.append((kind, value))
    return tokens


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def parse(tokens: List[tuple]) -> List[Any]:
    if not tokens:
        return []

    def parse_expr(i: int) -> tuple:
        kind, value = tokens[i]

        if kind == 'NUMBER':
            return int(value), i + 1
        elif kind == 'BOOLEAN':
            return True if value == '#t' else False, i + 1
        elif kind == 'SYMBOL':
            return Symbol(value), i + 1
        elif kind == 'QUOTE':
            # 'expr => (quote expr)
            quoted_expr, i = parse_expr(i + 1)
            return [Symbol('quote'), quoted_expr], i
        elif kind == 'LPAREN':
            return parse_list(i + 1)
        else:
            raise SyntaxError(f"Unexpected token: {value!r}")

    def parse_list(i: int) -> tuple:
        elements = []
        while i < len(tokens):
            kind, value = tokens[i]
            if kind == 'RPAREN':
                return elements, i + 1
            expr, i = parse_expr(i)
            elements.append(expr)
        raise SyntaxError("Unexpected end of input, expected ')'")

    expressions = []
    i = 0
    while i < len(tokens):
        expr, i = parse_expr(i)
        expressions.append(expr)
    return expressions


def parse_single(source: str) -> Any:
    tokens = tokenize(source)
    if not tokens:
        raise SyntaxError("Empty input")
    expressions = parse(tokens)
    if len(expressions) != 1:
        raise SyntaxError("Expected exactly one expression")
    return expressions[0]


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

class Environment:
    def __init__(self, parent: Optional['Environment'] = None):
        self.bindings: Dict[str, Any] = {}
        self.parent = parent

    def define(self, name: str, value: Any):
        self.bindings[name] = value

    def set(self, name: str, value: Any):
        if name in self.bindings:
            self.bindings[name] = value
        elif self.parent is not None:
            self.parent.set(name, value)
        else:
            raise NameError(f"Undefined variable: {name}")

    def lookup(self, name: str) -> Any:
        if name in self.bindings:
            return self.bindings[name]
        if self.parent is not None:
            return self.parent.lookup(name)
        raise NameError(f"Undefined symbol: {name}")


# ---------------------------------------------------------------------------
# Built-in Functions
# ---------------------------------------------------------------------------

def ensure_ints(args: List[Any], name: str) -> List[int]:
    for a in args:
        if not isinstance(a, int):
            raise TypeError(f"{name} requires integer arguments, got {type(a).__name__}")
    return args


def ensure_args_count(args: List[Any], expected: int, name: str):
    if len(args) != expected:
        raise ValueError(f"{name} expects {expected} argument(s), got {len(args)}")


def make_global_env() -> Environment:
    env = Environment()

    # Arithmetic
    def builtin_add(args):
        nums = ensure_ints(args, '+')
        if len(nums) == 0:
            raise ValueError("+ requires at least 1 argument")
        return sum(nums)

    def builtin_sub(args):
        nums = ensure_ints(args, '-')
        if len(nums) == 0:
            raise ValueError("- requires at least 1 argument")
        if len(nums) == 1:
            return -nums[0]
        return nums[0] - sum(nums[1:])

    def builtin_mul(args):
        nums = ensure_ints(args, '*')
        result = 1
        for n in nums:
            result *= n
        return result

    def builtin_div(args):
        nums = ensure_ints(args, '/')
        ensure_args_count(nums, 2, '/')
        if nums[1] == 0:
            raise ZeroDivisionError("Division by zero")
        return nums[0] // nums[1]

    def builtin_eq(args):
        nums = ensure_ints(args, '=')
        ensure_args_count(nums, 2, '=')
        return nums[0] == nums[1]

    def builtin_lt(args):
        nums = ensure_ints(args, '<')
        ensure_args_count(nums, 2, '<')
        return nums[0] < nums[1]

    def builtin_gt(args):
        nums = ensure_ints(args, '>')
        ensure_args_count(nums, 2, '>')
        return nums[0] > nums[1]

    # List operations
    def builtin_cons(args):
        ensure_args_count(args, 2, 'cons')
        if is_nil(args[1]):
            return [args[0]]
        if not isinstance(args[1], list):
            raise TypeError("cons second argument must be a list")
        return [args[0]] + args[1]

    def builtin_car(args):
        ensure_args_count(args, 1, 'car')
        if not isinstance(args[0], list) or is_nil(args[0]):
            raise TypeError("car requires a non-empty list")
        return args[0][0]

    def builtin_cdr(args):
        ensure_args_count(args, 1, 'cdr')
        if not isinstance(args[0], list) or is_nil(args[0]):
            raise TypeError("cdr requires a non-empty list")
        rest = args[0][1:]
        return rest if rest else NIL

    def builtin_list(args):
        return list(args)

    # Type predicates
    def builtin_nullp(args):
        ensure_args_count(args, 1, 'null?')
        return is_nil(args[0])

    def builtin_numberp(args):
        ensure_args_count(args, 1, 'number?')
        return isinstance(args[0], int)

    def builtin_symbolp(args):
        ensure_args_count(args, 1, 'symbol?')
        return isinstance(args[0], Symbol)

    def builtin_listp(args):
        ensure_args_count(args, 1, 'list?')
        return isinstance(args[0], list)

    env.define('+', builtin_add)
    env.define('-', builtin_sub)
    env.define('*', builtin_mul)
    env.define('/', builtin_div)
    env.define('=', builtin_eq)
    env.define('<', builtin_lt)
    env.define('>', builtin_gt)
    env.define('cons', builtin_cons)
    env.define('car', builtin_car)
    env.define('cdr', builtin_cdr)
    env.define('list', builtin_list)
    env.define('null?', builtin_nullp)
    env.define('number?', builtin_numberp)
    env.define('symbol?', builtin_symbolp)
    env.define('list?', builtin_listp)

    return env


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------

def evaluate(expr: Any, env: Environment) -> Any:
    # Self-evaluating
    if isinstance(expr, int):
        return expr
    if isinstance(expr, bool):
        return expr
    if is_nil(expr):
        return NIL

    # Symbol lookup
    if isinstance(expr, Symbol):
        return env.lookup(expr.name)

    # List expression
    if isinstance(expr, list):
        if is_nil(expr):
            return NIL

        # Special forms
        first = expr[0]
        if isinstance(first, Symbol):
            name = first.name

            if name == 'quote':
                if len(expr) != 2:
                    raise ValueError("quote expects exactly 1 argument")
                return expr[1]

            if name == 'define':
                if len(expr) != 3:
                    raise ValueError("define expects exactly 2 arguments")
                var_name = expr[1]
                if not isinstance(var_name, Symbol):
                    raise ValueError("define first argument must be a symbol")
                value = evaluate(expr[2], env)
                env.define(var_name.name, value)
                return None

            if name == 'if':
                if len(expr) not in (3, 4):
                    raise ValueError("if expects 2 or 3 arguments")
                condition = evaluate(expr[1], env)
                if condition is not False:
                    return evaluate(expr[2], env)
                elif len(expr) == 4:
                    return evaluate(expr[3], env)
                else:
                    return None

            if name == 'lambda':
                if len(expr) != 3:
                    raise ValueError("lambda expects exactly 2 arguments")
                params_expr = expr[1]
                if not isinstance(params_expr, list):
                    raise ValueError("lambda first argument must be a parameter list")
                params = []
                for p in params_expr:
                    if not isinstance(p, Symbol):
                        raise ValueError("lambda parameters must be symbols")
                    params.append(p.name)
                return Procedure(params, expr[2], env)

            if name == 'cond':
                clauses = expr[1:]
                for clause in clauses:
                    if not isinstance(clause, list) or len(clause) < 2:
                        raise ValueError("cond clauses must be lists with at least 2 elements")
                    condition = evaluate(clause[0], env)
                    if condition is not False:
                        # Evaluate all expressions in the clause, return last
                        result = None
                        for body_expr in clause[1:]:
                            result = evaluate(body_expr, env)
                        return result
                return None

        # Function application
        fn = evaluate(first, env)
        args = [evaluate(arg, env) for arg in expr[1:]]

        if callable(fn):
            return fn(args)
        elif isinstance(fn, Procedure):
            if len(args) != len(fn.params):
                raise ValueError(
                    f"Procedure expects {len(fn.params)} argument(s), got {len(args)}"
                )
            new_env = Environment(fn.closure_env)
            for param, arg in zip(fn.params, args):
                new_env.define(param, arg)
            return evaluate(fn.body, new_env)
        else:
            raise TypeError(f"Not a procedure: {fn}")

    raise TypeError(f"Unknown expression type: {type(expr).__name__}")


# ---------------------------------------------------------------------------
# REPL / Run helpers
# ---------------------------------------------------------------------------

def run(source: str, env: Optional[Environment] = None) -> Any:
    if env is None:
        env = make_global_env()
    tokens = tokenize(source)
    expressions = parse(tokens)
    result = None
    for expr in expressions:
        result = evaluate(expr, env)
    return result


def run_single(source: str, env: Optional[Environment] = None) -> Any:
    return run(source, env)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def run_tests():
    tests_passed = 0
    tests_failed = 0

    def check(name: str, actual: Any, expected: Any):
        nonlocal tests_passed, tests_failed
        # Handle None comparison carefully
        if actual == expected or (actual is None and expected is None):
            print(f"  PASS: {name}")
            tests_passed += 1
        else:
            print(f"  FAIL: {name} — expected {expected!r}, got {actual!r}")
            tests_failed += 1

    def expect_error(name: str, source: str, env: Optional[Environment] = None):
        nonlocal tests_passed, tests_failed
        try:
            run_single(source, env)
            print(f"  FAIL: {name} — expected an error but got none")
            tests_failed += 1
        except Exception as e:
            print(f"  PASS: {name} — correctly raised {type(e).__name__}: {e}")
            tests_passed += 1

    print("=" * 60)
    print("Running LISP Interpreter Tests")
    print("=" * 60)

    # Test 1: Basic arithmetic
    print("\n--- Basic Arithmetic ---")
    env = make_global_env()
    check("(+ 1 2)", run_single("(+ 1 2)", env), 3)
    check("(* (+ 1 2) (- 5 2))", run_single("(* (+ 1 2) (- 5 2))", env), 9)

    # Test 2: Variable definition
    print("\n--- Variable Definition ---")
    env = make_global_env()
    run_single("(define x 10)", env)
    check("(+ x 5)", run_single("(+ x 5)", env), 15)

    # Test 3: Factorial (recursion)
    print("\n--- Recursion (Factorial) ---")
    env = make_global_env()
    run_single("""
        (define factorial
            (lambda (n)
                (if (= n 0)
                    1
                    (* n (factorial (- n 1))))))
    """, env)
    check("(factorial 5)", run_single("(factorial 5)", env), 120)

    # Test 4: Lambda
    print("\n--- Lambda ---")
    env = make_global_env()
    run_single("(define square (lambda (x) (* x x)))", env)
    check("(square 7)", run_single("(square 7)", env), 49)

    # Test 5: cons/car/cdr
    print("\n--- List Operations ---")
    env = make_global_env()
    check("(cons 1 (cons 2 (cons 3 (list))))",
          run_single("(cons 1 (cons 2 (cons 3 (list))))", env),
          [1, 2, 3])
    check("(car (cons 1 (cons 2 (list))))",
          run_single("(car (cons 1 (cons 2 (list))))", env),
          1)
    check("(cdr (cons 1 (cons 2 (cons 3 (list)))))",
          run_single("(cdr (cons 1 (cons 2 (cons 3 (list)))))", env),
          [2, 3])

    # Test 6: quote
    print("\n--- Quote ---")
    env = make_global_env()
    result = run_single("(quote (1 2 3))", env)
    check("(quote (1 2 3))", result, [1, 2, 3])

    result2 = run_single("(quote (+ 1 2))", env)
    check("(quote (+ 1 2))", [isinstance(r, Symbol) and r.name or r for r in result2], ['+', 1, 2])

    # Test 7: Nested scopes
    print("\n--- Nested Scopes ---")
    env = make_global_env()
    run_single("(define x 5)", env)
    run_single("""
        (define foo
            (lambda (x)
                (+ x 10)))
    """, env)
    check("(foo 3)", run_single("(foo 3)", env), 13)
    check("x is still 5", run_single("x", env), 5)

    # Test 8: cond
    print("\n--- Cond ---")
    env = make_global_env()
    run_single("(define grade 85)", env)
    run_single("""
        (define letter
            (lambda (score)
                (cond
                    ((> score 90) 'A)
                    ((> score 80) 'B)
                    ((> score 70) 'C)
                    (else 'F))))
    """, env)
    # Need to define 'else as true for cond to work with else clause
    env.define('else', True)
    check("(letter 85)", run_single("(letter 85)", env), Symbol('B'))

    # Better cond test without else symbol dependency
    env2 = make_global_env()
    run_single("(define x 10)", env2)
    result_cond = run_single("""
        (cond
            ((> x 20) 100)
            ((> x 5) 50)
            ((= x 10) 999))
    """, env2)
    check("cond with (> x 5)", result_cond, 50)

    # Test 9: Error handling
    print("\n--- Error Handling ---")
    env = make_global_env()
    expect_error("undefined symbol", "(+ x 1)", env)
    expect_error("too few args for +", "(+)", env)
    expect_error("too few args for car", "(car)", env)
    expect_error("too many args for car", "(car 1 2)", env)

    # Test 10: Type predicates
    print("\n--- Type Predicates ---")
    env = make_global_env()
    check("(number? 42)", run_single("(number? 42)", env), True)
    check("(number? (quote a))", run_single("(number? (quote a))", env), False)
    check("(null? (list))", run_single("(null? (list))", env), True)
    check("(null? (cons 1 (list)))", run_single("(null? (cons 1 (list)))", env), False)
    check("(list? (cons 1 (list)))", run_single("(list? (cons 1 (list)))", env), True)
    check("(symbol? (quote hello))", run_single("(symbol? (quote hello))", env), True)

    # Test 11: Complex nested expression
    print("\n--- Complex Expression ---")
    env = make_global_env()
    run_single("(define add (lambda (a b) (+ a b)))", env)
    run_single("(define double (lambda (x) (* x 2)))", env)
    check("nested: (double (add 3 4))", run_single("(double (add 3 4))", env), 14)

    # Summary
    print("\n" + "=" * 60)
    print(f"Results: {tests_passed} passed, {tests_failed} failed")
    print("=" * 60)
    return tests_passed, tests_failed


if __name__ == "__main__":
    passed, failed = run_tests()
    exit(0 if failed == 0 else 1)
