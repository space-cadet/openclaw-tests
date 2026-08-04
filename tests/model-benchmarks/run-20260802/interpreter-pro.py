#!/usr/bin/env python3
"""
Minimal LISP Interpreter in Python

Supports:
- Data types: integers, booleans (#t/#f), symbols, lists
- Built-ins: +, -, *, /, =, <, >, cons, car, cdr, list, null?, number?, symbol?, list?
- Special forms: define, lambda, if, quote, cond
- Lexical scoping with recursion support
- Meaningful error reporting
"""

import re
from typing import Any, Dict, List, Optional, Tuple

# =============================================================================
# DATA TYPES
# =============================================================================

class Symbol:
    """A LISP symbol."""
    __slots__ = ('name',)

    def __init__(self, name: str):
        self.name = name

    def __eq__(self, other):
        return isinstance(other, Symbol) and self.name == other.name

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return self.name


class Boolean:
    """A LISP boolean (#t or #f). Only #f is falsey."""
    __slots__ = ('value',)

    def __init__(self, value: bool):
        self.value = value

    def __bool__(self):
        return self.value

    def __eq__(self, other):
        return isinstance(other, Boolean) and self.value == other.value

    def __repr__(self):
        return '#t' if self.value else '#f'


# Singletons for booleans
TRUE = Boolean(True)
FALSE = Boolean(False)


class Procedure:
    """User-defined lambda procedure. Captures defining env for lexical scoping."""
    __slots__ = ('params', 'body', 'env')

    def __init__(self, params: List[Symbol], body: List[Any], env: 'Environment'):
        self.params = params
        self.body = body
        self.env = env

    def __repr__(self):
        return '#<procedure>'


class LispError(Exception):
    """Runtime error in the LISP interpreter."""
    pass


# =============================================================================
# LEXER
# =============================================================================

TOKEN_PATTERNS = [
    ('COMMENT', r';[^\n]*'),
    ('LPAREN', r'\('),
    ('RPAREN', r'\)'),
    ('QUOTE', r"'"),
    ('BOOL', r'#[tf]'),
    ('NUMBER', r'-?\d+'),
    ('SYMBOL', r"[^\s()\[\]{};'`,]+"),
    ('WHITESPACE', r'\s+'),
]

TOKEN_REGEX = re.compile(
    '|'.join(f'(?P<{name}>{pattern})' for name, pattern in TOKEN_PATTERNS)
)


def tokenize(source: str) -> List[Tuple[str, str]]:
    """Convert source string into a list of (kind, value) tokens."""
    tokens = []
    for match in TOKEN_REGEX.finditer(source):
        kind = match.lastgroup
        value = match.group()
        if kind in ('WHITESPACE', 'COMMENT'):
            continue
        tokens.append((kind, value))
    return tokens


# =============================================================================
# PARSER
# =============================================================================

class ParseError(Exception):
    pass


def parse(tokens: List[Tuple[str, str]]) -> List[Any]:
    """Parse all expressions from tokens."""
    exprs = []
    while tokens:
        expr, tokens = parse_expr(tokens)
        exprs.append(expr)
    return exprs


def parse_expr(tokens: List[Tuple[str, str]]) -> Tuple[Any, List[Tuple[str, str]]]:
    """Parse a single expression."""
    if not tokens:
        raise ParseError("unexpected end of input")

    kind, value = tokens[0]
    rest = tokens[1:]

    if kind == 'NUMBER':
        return int(value), rest
    elif kind == 'BOOL':
        return (TRUE if value == '#t' else FALSE), rest
    elif kind == 'SYMBOL':
        return Symbol(value), rest
    elif kind == 'QUOTE':
        if not rest:
            raise ParseError("unexpected end of input after quote")
        quoted, rest = parse_expr(rest)
        return [Symbol('quote'), quoted], rest
    elif kind == 'LPAREN':
        return parse_list(rest)
    else:
        raise ParseError(f"unexpected token: {value}")


def parse_list(tokens: List[Tuple[str, str]]) -> Tuple[List[Any], List[Tuple[str, str]]]:
    """Parse the contents of a parenthesized list."""
    result = []
    while tokens:
        kind, value = tokens[0]
        if kind == 'RPAREN':
            return result, tokens[1:]
        expr, tokens = parse_expr(tokens)
        result.append(expr)
    raise ParseError("missing closing parenthesis")


# =============================================================================
# ENVIRONMENT (Lexical Scoping)
# =============================================================================

class Environment:
    """A chain of binding frames. Each frame is a dict with an optional parent."""

    def __init__(self, parent: Optional['Environment'] = None):
        self.bindings: Dict[Symbol, Any] = {}
        self.parent = parent

    def define(self, name: Symbol, value: Any):
        """Add a new binding in the current frame."""
        self.bindings[name] = value

    def lookup(self, name: Symbol) -> Any:
        """Look up a name, searching up the parent chain."""
        if name in self.bindings:
            return self.bindings[name]
        if self.parent is not None:
            return self.parent.lookup(name)
        raise LispError(f"undefined symbol: {name}")


# =============================================================================
# BUILT-IN PROCEDURES
# =============================================================================

def _check_arity(name: str, args: List[Any], expected: int):
    if len(args) != expected:
        raise LispError(f"{name}: expected {expected} argument(s), got {len(args)}")


def builtin_add(args: List[Any]) -> int:
    if not all(isinstance(a, int) for a in args):
        raise LispError("+: all arguments must be numbers")
    return sum(args)


def builtin_sub(args: List[Any]) -> int:
    if not args:
        raise LispError("-: requires at least 1 argument")
    if not all(isinstance(a, int) for a in args):
        raise LispError("-: all arguments must be numbers")
    if len(args) == 1:
        return -args[0]
    result = args[0]
    for a in args[1:]:
        result -= a
    return result


def builtin_mul(args: List[Any]) -> int:
    if not all(isinstance(a, int) for a in args):
        raise LispError("*: all arguments must be numbers")
    result = 1
    for a in args:
        result *= a
    return result


def builtin_div(args: List[Any]) -> int:
    if not args:
        raise LispError("/: requires at least 1 argument")
    if not all(isinstance(a, int) for a in args):
        raise LispError("/: all arguments must be numbers")
    if len(args) == 1:
        return 1 // args[0]
    result = args[0]
    for a in args[1:]:
        result //= a
    return result


def builtin_eq(args: List[Any]) -> Boolean:
    _check_arity("=", args, 2)
    return TRUE if args[0] == args[1] else FALSE


def builtin_lt(args: List[Any]) -> Boolean:
    _check_arity("<", args, 2)
    return TRUE if args[0] < args[1] else FALSE


def builtin_gt(args: List[Any]) -> Boolean:
    _check_arity(">", args, 2)
    return TRUE if args[0] > args[1] else FALSE


def builtin_cons(args: List[Any]) -> List[Any]:
    _check_arity("cons", args, 2)
    if not isinstance(args[1], list):
        raise LispError("cons: second argument must be a list")
    return [args[0]] + args[1]


def builtin_car(args: List[Any]) -> Any:
    _check_arity("car", args, 1)
    if not isinstance(args[0], list) or not args[0]:
        raise LispError("car: expected non-empty list")
    return args[0][0]


def builtin_cdr(args: List[Any]) -> List[Any]:
    _check_arity("cdr", args, 1)
    if not isinstance(args[0], list):
        raise LispError("cdr: expected list")
    return args[0][1:]


def builtin_list(args: List[Any]) -> List[Any]:
    return list(args)


def builtin_null_q(args: List[Any]) -> Boolean:
    _check_arity("null?", args, 1)
    return TRUE if isinstance(args[0], list) and len(args[0]) == 0 else FALSE


def builtin_number_q(args: List[Any]) -> Boolean:
    _check_arity("number?", args, 1)
    return TRUE if isinstance(args[0], int) else FALSE


def builtin_symbol_q(args: List[Any]) -> Boolean:
    _check_arity("symbol?", args, 1)
    return TRUE if isinstance(args[0], Symbol) else FALSE


def builtin_list_q(args: List[Any]) -> Boolean:
    _check_arity("list?", args, 1)
    return TRUE if isinstance(args[0], list) else FALSE


def make_global_env() -> Environment:
    """Create the global environment with all built-in procedures."""
    env = Environment()
    env.define(Symbol('+'), builtin_add)
    env.define(Symbol('-'), builtin_sub)
    env.define(Symbol('*'), builtin_mul)
    env.define(Symbol('/'), builtin_div)
    env.define(Symbol('='), builtin_eq)
    env.define(Symbol('<'), builtin_lt)
    env.define(Symbol('>'), builtin_gt)
    env.define(Symbol('cons'), builtin_cons)
    env.define(Symbol('car'), builtin_car)
    env.define(Symbol('cdr'), builtin_cdr)
    env.define(Symbol('list'), builtin_list)
    env.define(Symbol('null?'), builtin_null_q)
    env.define(Symbol('number?'), builtin_number_q)
    env.define(Symbol('symbol?'), builtin_symbol_q)
    env.define(Symbol('list?'), builtin_list_q)
    return env


# =============================================================================
# EVALUATOR
# =============================================================================

def evaluate(expr: Any, env: Environment) -> Any:
    """Evaluate an expression in the given environment."""

    # Literals
    if isinstance(expr, int):
        return expr
    if isinstance(expr, Boolean):
        return expr

    # Variable reference
    if isinstance(expr, Symbol):
        return env.lookup(expr)

    # Empty list evaluates to itself
    if isinstance(expr, list):
        if len(expr) == 0:
            return expr
    else:
        raise LispError(f"unknown expression type: {type(expr).__name__}")

    first = expr[0]

    # ----- Special Forms -----

    # (quote expr)
    if first == Symbol('quote'):
        if len(expr) != 2:
            raise LispError("quote: requires exactly 1 argument")
        return expr[1]

    # (define name value)  OR  (define (name args...) body...)
    if first == Symbol('define'):
        if len(expr) < 3:
            raise LispError("define: requires at least 2 arguments")

        if isinstance(expr[1], Symbol):
            # (define name value)
            if len(expr) != 3:
                raise LispError("define: bad syntax")
            name = expr[1]
            value = evaluate(expr[2], env)
            env.define(name, value)
            return None

        elif isinstance(expr[1], list):
            # (define (name args...) body...)  => syntactic sugar
            if len(expr[1]) < 1:
                raise LispError("define: bad syntax")
            name = expr[1][0]
            if not isinstance(name, Symbol):
                raise LispError("define: function name must be a symbol")
            raw_params = expr[1][1:]
            for p in raw_params:
                if not isinstance(p, Symbol):
                    raise LispError("define: parameters must be symbols")
            params = [Symbol(p.name) for p in raw_params]
            body = expr[2:]

            # Create recursive environment so the procedure can call itself
            rec_env = Environment(env)
            proc = Procedure(params, body, rec_env)
            rec_env.define(name, proc)
            env.define(name, proc)
            return None
        else:
            raise LispError("define: bad syntax")

    # (lambda (params...) body...)
    if first == Symbol('lambda'):
        if len(expr) < 3:
            raise LispError("lambda: requires at least 2 arguments")
        raw_params = expr[1]
        if not isinstance(raw_params, list):
            raise LispError("lambda: parameters must be a list")
        for p in raw_params:
            if not isinstance(p, Symbol):
                raise LispError("lambda: parameters must be symbols")
        body = expr[2:]
        return Procedure(raw_params, body, env)

    # (if condition then [else])
    if first == Symbol('if'):
        if len(expr) not in (3, 4):
            raise LispError("if: requires 2 or 3 arguments")
        cond = evaluate(expr[1], env)
        if cond is not FALSE:
            return evaluate(expr[2], env)
        elif len(expr) == 4:
            return evaluate(expr[3], env)
        else:
            return None

    # (cond (test expr...) ... [(else expr...)])
    if first == Symbol('cond'):
        for clause in expr[1:]:
            if not isinstance(clause, list) or len(clause) < 1:
                raise LispError("cond: bad clause")
            test = clause[0]
            if test == Symbol('else'):
                result = None
                for e in clause[1:]:
                    result = evaluate(e, env)
                return result
            else:
                val = evaluate(test, env)
                if val is not FALSE:
                    result = None
                    for e in clause[1:]:
                        result = evaluate(e, env)
                    return result
        return None

    # ----- Function Application -----
    func = evaluate(first, env)
    args = [evaluate(arg, env) for arg in expr[1:]]

    if callable(func) and not isinstance(func, Procedure):
        # Built-in procedure
        return func(args)

    if isinstance(func, Procedure):
        # User-defined procedure: extend captured env with arguments
        if len(args) != len(func.params):
            raise LispError(
                f"expected {len(func.params)} argument(s), got {len(args)}"
            )
        new_env = Environment(func.env)
        for param, arg in zip(func.params, args):
            new_env.define(param, arg)
        result = None
        for body_expr in func.body:
            result = evaluate(body_expr, new_env)
        return result

    raise LispError(f"not a procedure: {func}")


# =============================================================================
# REPR
# =============================================================================

def lisp_repr(obj: Any) -> str:
    """Convert a LISP value to its string representation."""
    if isinstance(obj, int):
        return str(obj)
    if isinstance(obj, Boolean):
        return '#t' if obj.value else '#f'
    if isinstance(obj, Symbol):
        return obj.name
    if isinstance(obj, list):
        return '(' + ' '.join(lisp_repr(x) for x in obj) + ')'
    if isinstance(obj, Procedure):
        return '#<procedure>'
    if obj is None:
        return '()'
    return str(obj)


# =============================================================================
# DRIVER
# =============================================================================

def run(source: str, env: Optional[Environment] = None) -> Any:
    """Evaluate all expressions in source and return the last result."""
    tokens = tokenize(source)
    exprs = parse(tokens)
    if env is None:
        env = make_global_env()
    result = None
    for expr in exprs:
        result = evaluate(expr, env)
    return result


def run_env(source: str, env: Optional[Environment] = None) -> Tuple[Any, Environment]:
    """Evaluate all expressions and return (last_result, env)."""
    tokens = tokenize(source)
    exprs = parse(tokens)
    if env is None:
        env = make_global_env()
    result = None
    for expr in exprs:
        result = evaluate(expr, env)
    return result, env


# =============================================================================
# TESTS
# =============================================================================

def run_tests() -> bool:
    print("=" * 60)
    print("Running LISP Interpreter Tests")
    print("=" * 60)

    passed = 0
    failed = 0

    def check(name: str, got: Any, expected: Any, expect_error: bool = False):
        nonlocal passed, failed
        if expect_error:
            print(f"  FAIL  {name}")
            print(f"        Expected error, got: {lisp_repr(got)}")
            failed += 1
            return
        if got == expected:
            print(f"  PASS  {name}")
            passed += 1
        else:
            print(f"  FAIL  {name}")
            print(f"        Expected: {lisp_repr(expected)}")
            print(f"        Got:      {lisp_repr(got)}")
            failed += 1

    def check_error(name: str, error: Exception, expected_substring: str):
        nonlocal passed, failed
        msg = str(error).lower()
        if expected_substring.lower() in msg:
            print(f"  PASS  {name}  (Error: {error})")
            passed += 1
        else:
            print(f"  FAIL  {name}")
            print(f"        Error missing '{expected_substring}': {error}")
            failed += 1

    # ------------------------------------------------------------------
    # Test 1: (+ 1 2) => 3
    # ------------------------------------------------------------------
    print("\n[1] Basic addition")
    try:
        result = run("(+ 1 2)")
        check("(+ 1 2) => 3", result, 3)
    except Exception as e:
        check_error("(+ 1 2) => 3", e, "error")

    # ------------------------------------------------------------------
    # Test 2: (* (+ 1 2) (- 5 2)) => 9
    # ------------------------------------------------------------------
    print("\n[2] Nested arithmetic")
    try:
        result = run("(* (+ 1 2) (- 5 2))")
        check("(* (+ 1 2) (- 5 2)) => 9", result, 9)
    except Exception as e:
        check_error("(* (+ 1 2) (- 5 2)) => 9", e, "error")

    # ------------------------------------------------------------------
    # Test 3: (define x 10), (+ x 5) => 15
    # ------------------------------------------------------------------
    print("\n[3] Variable definition and lookup")
    try:
        _, env = run_env("(define x 10)")
        result = run("(+ x 5)", env)
        check("(define x 10), (+ x 5) => 15", result, 15)
    except Exception as e:
        check_error("(define x 10), (+ x 5) => 15", e, "error")

    # ------------------------------------------------------------------
    # Test 4: (define (factorial n) ...) (factorial 5) => 120
    # ------------------------------------------------------------------
    print("\n[4] Recursive function (factorial)")
    try:
        src = """
            (define (factorial n)
              (if (= n 0)
                  1
                  (* n (factorial (- n 1)))))
            (factorial 5)
        """
        result = run(src)
        check("(factorial 5) => 120", result, 120)
    except Exception as e:
        check_error("(factorial 5) => 120", e, "error")

    # ------------------------------------------------------------------
    # Test 5: (define square (lambda (x) (* x x))) (square 7) => 49
    # ------------------------------------------------------------------
    print("\n[5] Lambda definition and application")
    try:
        src = """
            (define square (lambda (x) (* x x)))
            (square 7)
        """
        result = run(src)
        check("(square 7) => 49", result, 49)
    except Exception as e:
        check_error("(square 7) => 49", e, "error")

    # ------------------------------------------------------------------
    # Test 6: (cons 1 (cons 2 (cons 3 '()))) => (1 2 3)
    # ------------------------------------------------------------------
    print("\n[6] List construction with cons")
    try:
        result = run("(cons 1 (cons 2 (cons 3 '())))")
        check("(cons 1 (cons 2 (cons 3 '()))) => (1 2 3)", result, [1, 2, 3])
    except Exception as e:
        check_error("(cons 1 (cons 2 (cons 3 '()))) => (1 2 3)", e, "error")

    # ------------------------------------------------------------------
    # Test 7: (car (list 1 2 3)) => 1
    # ------------------------------------------------------------------
    print("\n[7] car")
    try:
        result = run("(car (list 1 2 3))")
        check("(car (list 1 2 3)) => 1", result, 1)
    except Exception as e:
        check_error("(car (list 1 2 3)) => 1", e, "error")

    # ------------------------------------------------------------------
    # Test 8: (cdr (list 1 2 3)) => (2 3)
    # ------------------------------------------------------------------
    print("\n[8] cdr")
    try:
        result = run("(cdr (list 1 2 3))")
        check("(cdr (list 1 2 3)) => (2 3)", result, [2, 3])
    except Exception as e:
        check_error("(cdr (list 1 2 3)) => (2 3)", e, "error")

    # ------------------------------------------------------------------
    # Test 9: (quote (+ 1 2)) => (+ 1 2)
    # ------------------------------------------------------------------
    print("\n[9] Quoting an expression")
    try:
        result = run("(quote (+ 1 2))")
        check("(quote (+ 1 2)) => (+ 1 2)", result, [Symbol('+'), 1, 2])
    except Exception as e:
        check_error("(quote (+ 1 2)) => (+ 1 2)", e, "error")

    # ------------------------------------------------------------------
    # Test 10: (quote (a b c)) => (a b c)
    # ------------------------------------------------------------------
    print("\n[10] Quoting a list of symbols")
    try:
        result = run("(quote (a b c))")
        check("(quote (a b c)) => (a b c)", result,
              [Symbol('a'), Symbol('b'), Symbol('c')])
    except Exception as e:
        check_error("(quote (a b c)) => (a b c)", e, "error")

    # ------------------------------------------------------------------
    # Test 11: Nested scopes
    # ------------------------------------------------------------------
    print("\n[11] Nested scopes (lexical scoping)")
    try:
        src = """
            (define x 5)
            (define (foo x) (+ x 10))
            (foo 3)
        """
        result, env = run_env(src)
        x_val = env.lookup(Symbol('x'))
        check("(foo 3) => 13", result, 13)
        if x_val == 5:
            print(f"  PASS  x still 5 after (foo 3)")
            passed += 1
        else:
            print(f"  FAIL  x still 5 after (foo 3)")
            print(f"        Expected: 5")
            print(f"        Got:      {lisp_repr(x_val)}")
            failed += 1
    except Exception as e:
        check_error("Nested scopes", e, "error")

    # ------------------------------------------------------------------
    # Test 12: (cond ((> 5 3) 'yes) (else 'no)) => yes
    # ------------------------------------------------------------------
    print("\n[12] cond")
    try:
        result = run("(cond ((> 5 3) 'yes) (else 'no))")
        check("(cond ((> 5 3) 'yes) (else 'no)) => yes", result, Symbol('yes'))
    except Exception as e:
        check_error("cond", e, "error")

    # ------------------------------------------------------------------
    # Test 13: (factorial) => Error: too few arguments
    # ------------------------------------------------------------------
    print("\n[13] Arity error")
    try:
        # First define factorial, then call with no args
        src = """
            (define (factorial n)
              (if (= n 0)
                  1
                  (* n (factorial (- n 1)))))
            (factorial)
        """
        result = run(src)
        check("(factorial) => Error", result, None, expect_error=True)
    except LispError as e:
        check_error("(factorial) => Error: too few arguments", e, "expected")
    except Exception as e:
        check_error("(factorial) => Error: too few arguments", e, "expected")

    # ------------------------------------------------------------------
    # Test 14: (undefined 1) => Error: undefined symbol
    # ------------------------------------------------------------------
    print("\n[14] Undefined symbol error")
    try:
        result = run("(undefined 1)")
        check("(undefined 1) => Error", result, None, expect_error=True)
    except LispError as e:
        check_error("(undefined 1) => Error: undefined symbol", e, "undefined")
    except Exception as e:
        check_error("(undefined 1) => Error: undefined symbol", e, "undefined")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    return failed == 0


if __name__ == '__main__':
    success = run_tests()
    exit(0 if success else 1)
