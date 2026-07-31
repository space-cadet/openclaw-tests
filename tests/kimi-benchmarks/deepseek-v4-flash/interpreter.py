#!/usr/bin/env python3
"""
Minimal LISP Interpreter in Python
No eval(), ast, or parsing libraries used.
Supports lexical scoping, recursion, and built-in/special forms.
"""

import re
from typing import Any, Dict, List, Optional, Callable, Union


# ============================
# Errors
# ============================
class LispError(Exception):
    """Base error for the LISP interpreter."""
    pass


class UndefinedSymbolError(LispError):
    pass


class TypeError(LispError):
    pass


class ArgumentError(LispError):
    pass


class SyntaxError(LispError):
    pass


# ============================
# Data Types
# ============================
class Symbol:
    """Represents a LISP symbol."""
    def __init__(self, name: str):
        self.name = name

    def __eq__(self, other):
        return isinstance(other, Symbol) and self.name == other.name

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return f"Symbol({self.name})"

    def __str__(self):
        return self.name


# Unique sentinel for empty list / nil
class _NilClass:
    """The nil / empty list singleton."""
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    def __repr__(self):
        return "nil"
    def __eq__(self, other):
        return isinstance(other, _NilClass)


NIL = _NilClass()


class Cons:
    """A LISP cons cell (car . cdr)."""
    def __init__(self, car: Any, cdr: Any):
        self.car = car
        self.cdr = cdr

    def to_list(self) -> List[Any]:
        """Convert cons chain to Python list."""
        result = []
        current = self
        while isinstance(current, Cons):
            result.append(current.car)
            current = current.cdr
        if current is not NIL:
            raise LispError("Not a proper list")
        return result

    @staticmethod
    def from_list(pylist: List[Any]) -> Any:
        """Convert Python list to cons chain."""
        result = NIL
        for item in reversed(pylist):
            result = Cons(item, result)
        return result

    def __repr__(self):
        items = []
        current = self
        while isinstance(current, Cons):
            items.append(repr(current.car))
            current = current.cdr
        if current is NIL:
            return "(" + " ".join(items) + ")"
        else:
            return "(" + " ".join(items) + " . " + repr(current) + ")"


# ============================
# Environment (Lexical Scoping)
# ============================
class Environment:
    """A LISP environment with lexical scoping."""
    def __init__(self, parent: Optional['Environment'] = None):
        self.bindings: Dict[str, Any] = {}
        self.parent = parent

    def define(self, name: str, value: Any) -> None:
        """Define a binding in the current environment."""
        self.bindings[name] = value

    def set(self, name: str, value: Any) -> None:
        """Set an existing binding (searches up the chain)."""
        if name in self.bindings:
            self.bindings[name] = value
            return
        if self.parent is not None:
            self.parent.set(name, value)
            return
        raise UndefinedSymbolError(f"Undefined symbol: {name}")

    def lookup(self, name: str) -> Any:
        """Look up a symbol (searches up the chain)."""
        if name in self.bindings:
            return self.bindings[name]
        if self.parent is not None:
            return self.parent.lookup(name)
        raise UndefinedSymbolError(f"Undefined symbol: {name}")

    def extend(self, params: List[str], args: List[Any]) -> 'Environment':
        """Create a child environment with params bound to args."""
        if len(params) != len(args):
            raise ArgumentError(
                f"Expected {len(params)} arguments, got {len(args)}"
            )
        child = Environment(parent=self)
        for p, a in zip(params, args):
            child.define(p, a)
        return child


# ============================
# Tokenizer (Lexer)
# ============================
TOKEN_PATTERN = re.compile(r'''
    (?P<LPAREN>\()               |
    (?P<RPAREN>\))               |
    (?P<QUOTE>')                  |
    (?P<BOOLEAN>\#t|\#f)         |
    (?P<NUMBER>-?\d+)            |
    (?P<SYMBOL>[^\s()\'"]+)     |
    (?P<STRING>"(?:[^"\\]|\\.)*") |
    (?P<SKIP>\s+|;[^\n]*)        |
    (?P<MISMATCH>.)
''', re.VERBOSE)


def tokenize(source: str) -> List[Any]:
    """Tokenize LISP source code into a list of tokens."""
    tokens = []
    for match in TOKEN_PATTERN.finditer(source):
        kind = match.lastgroup
        value = match.group()
        if kind == 'SKIP':
            continue
        elif kind == 'LPAREN':
            tokens.append('LPAREN')
        elif kind == 'RPAREN':
            tokens.append('RPAREN')
        elif kind == 'QUOTE':
            tokens.append('QUOTE')
        elif kind == 'BOOLEAN':
            tokens.append(value == '#t')
        elif kind == 'NUMBER':
            tokens.append(int(value))
        elif kind == 'SYMBOL':
            tokens.append(Symbol(value))
        elif kind == 'STRING':
            # Simple string support
            tokens.append(value[1:-1])
        elif kind == 'MISMATCH':
            raise SyntaxError(f"Unexpected character: {value!r}")
    return tokens


# ============================
# Parser
# ============================
def parse(tokens: List[Any]) -> List[Any]:
    """Parse tokens into LISP expressions."""
    if not tokens:
        return []
    expressions = []
    while tokens:
        expressions.append(parse_expr(tokens))
    return expressions


def parse_expr(tokens: List[Any]) -> Any:
    """Parse a single expression from tokens."""
    if not tokens:
        raise SyntaxError("Unexpected end of input")

    token = tokens.pop(0)

    if token == 'LPAREN':
        return parse_list(tokens)
    elif token == 'QUOTE':
        # 'expr => (quote expr)
        expr = parse_expr(tokens)
        return [Symbol('quote'), expr]
    elif isinstance(token, (int, bool, str)):
        return token
    elif isinstance(token, Symbol):
        return token
    else:
        raise SyntaxError(f"Unexpected token: {token}")


def parse_list(tokens: List[Any]) -> List[Any]:
    """Parse the contents of a list until RPAREN."""
    lst = []
    while tokens and tokens[0] != 'RPAREN':
        lst.append(parse_expr(tokens))
    if not tokens:
        raise SyntaxError("Missing closing parenthesis")
    tokens.pop(0)  # consume RPAREN
    return lst


# ============================
# Built-in Procedures
# ============================
def make_builtin(name: str, fn: Callable, min_args: Optional[int] = None,
                 max_args: Optional[int] = None) -> 'Procedure':
    """Create a built-in procedure wrapper."""
    return Procedure(
        name=name,
        params=None,
        body=None,
        env=None,
        builtin=fn,
        min_args=min_args,
        max_args=max_args
    )


class Procedure:
    """A LISP procedure (lambda or built-in)."""
    def __init__(self, name: str, params: Optional[List[str]],
                 body: Optional[Any], env: Optional[Environment],
                 builtin: Optional[Callable] = None,
                 min_args: Optional[int] = None,
                 max_args: Optional[int] = None,
                 is_macro: bool = False):
        self.name = name
        self.params = params
        self.body = body
        self.env = env
        self.builtin = builtin
        self.min_args = min_args
        self.max_args = max_args
        self.is_macro = is_macro

    def __repr__(self):
        return f"#<procedure:{self.name}>"

    def call(self, args: List[Any]) -> Any:
        """Call the procedure with the given evaluated arguments."""
        if self.builtin:
            if self.min_args is not None and len(args) < self.min_args:
                raise ArgumentError(
                    f"{self.name}: expected at least {self.min_args} arguments, "
                    f"got {len(args)}"
                )
            if self.max_args is not None and len(args) > self.max_args:
                raise ArgumentError(
                    f"{self.name}: expected at most {self.max_args} arguments, "
                    f"got {len(args)}"
                )
            return self.builtin(args)
        else:
            # Lambda
            if self.params is None or self.env is None:
                raise LispError("Invalid lambda")
            local_env = self.env.extend(self.params, args)
            return eval_expr(self.body, local_env)


def _plus(args: List[Any]) -> int:
    if not all(isinstance(a, int) for a in args):
        raise TypeError("+: all arguments must be numbers")
    return sum(args)


def _minus(args: List[Any]) -> int:
    if len(args) == 0:
        raise ArgumentError("-: requires at least 1 argument")
    if not all(isinstance(a, int) for a in args):
        raise TypeError("-: all arguments must be numbers")
    if len(args) == 1:
        return -args[0]
    result = args[0]
    for a in args[1:]:
        result -= a
    return result


def _multiply(args: List[Any]) -> int:
    if not all(isinstance(a, int) for a in args):
        raise TypeError("*: all arguments must be numbers")
    result = 1
    for a in args:
        result *= a
    return result


def _divide(args: List[Any]) -> int:
    if len(args) == 0:
        raise ArgumentError("/: requires at least 1 argument")
    if not all(isinstance(a, int) for a in args):
        raise TypeError("/: all arguments must be numbers")
    if len(args) == 1:
        return 1 // args[0]
    result = args[0]
    for a in args[1:]:
        if a == 0:
            raise LispError("Division by zero")
        result //= a
    return result


def _equal(args: List[Any]) -> bool:
    if len(args) != 2:
        raise ArgumentError("=: requires exactly 2 arguments")
    return args[0] == args[1]


def _less(args: List[Any]) -> bool:
    if len(args) != 2:
        raise ArgumentError("<: requires exactly 2 arguments")
    if not all(isinstance(a, int) for a in args):
        raise TypeError("<: arguments must be numbers")
    return args[0] < args[1]


def _greater(args: List[Any]) -> bool:
    if len(args) != 2:
        raise ArgumentError(">: requires exactly 2 arguments")
    if not all(isinstance(a, int) for a in args):
        raise TypeError(">: arguments must be numbers")
    return args[0] > args[1]


def _cons(args: List[Any]) -> Any:
    if len(args) != 2:
        raise ArgumentError("cons: requires exactly 2 arguments")
    return Cons(args[0], args[1])


def _car(args: List[Any]) -> Any:
    if len(args) != 1:
        raise ArgumentError("car: requires exactly 1 argument")
    arg = args[0]
    if isinstance(arg, Cons):
        return arg.car
    raise TypeError(f"car: expected cons, got {type(arg).__name__}")


def _cdr(args: List[Any]) -> Any:
    if len(args) != 1:
        raise ArgumentError("cdr: requires exactly 1 argument")
    arg = args[0]
    if isinstance(arg, Cons):
        return arg.cdr
    raise TypeError(f"cdr: expected cons, got {type(arg).__name__}")


def _list_fn(args: List[Any]) -> Any:
    """Built-in list: creates a proper list from arguments."""
    return Cons.from_list(args)


def _nullp(args: List[Any]) -> bool:
    if len(args) != 1:
        raise ArgumentError("null?: requires exactly 1 argument")
    return args[0] is NIL


def _numberp(args: List[Any]) -> bool:
    if len(args) != 1:
        raise ArgumentError("number?: requires exactly 1 argument")
    return isinstance(args[0], int)


def _symbolp(args: List[Any]) -> bool:
    if len(args) != 1:
        raise ArgumentError("symbol?: requires exactly 1 argument")
    return isinstance(args[0], Symbol)


def _listp(args: List[Any]) -> bool:
    if len(args) != 1:
        raise ArgumentError("list?: requires exactly 1 argument")
    arg = args[0]
    if arg is NIL:
        return True
    return isinstance(arg, Cons)


def setup_global_env() -> Environment:
    """Create the global environment with built-in procedures."""
    env = Environment()
    env.define("+", make_builtin("+", _plus, min_args=0))
    env.define("-", make_builtin("-", _minus, min_args=1))
    env.define("*", make_builtin("*", _multiply, min_args=0))
    env.define("/", make_builtin("/", _divide, min_args=1))
    env.define("=", make_builtin("=", _equal, min_args=2, max_args=2))
    env.define("<", make_builtin("<", _less, min_args=2, max_args=2))
    env.define(">", make_builtin(">", _greater, min_args=2, max_args=2))
    env.define("cons", make_builtin("cons", _cons, min_args=2, max_args=2))
    env.define("car", make_builtin("car", _car, min_args=1, max_args=1))
    env.define("cdr", make_builtin("cdr", _cdr, min_args=1, max_args=1))
    env.define("list", make_builtin("list", _list_fn, min_args=0))
    env.define("null?", make_builtin("null?", _nullp, min_args=1, max_args=1))
    env.define("number?", make_builtin("number?", _numberp, min_args=1, max_args=1))
    env.define("symbol?", make_builtin("symbol?", _symbolp, min_args=1, max_args=1))
    env.define("list?", make_builtin("list?", _listp, min_args=1, max_args=1))
    return env


# ============================
# Evaluator
# ============================
def eval_expr(expr: Any, env: Environment) -> Any:
    """Evaluate a LISP expression in the given environment."""
    # Self-evaluating
    if isinstance(expr, (int, bool)):
        return expr
    if expr is NIL:
        return NIL
    if isinstance(expr, str):
        return expr  # string literal
    if isinstance(expr, Cons):
        return expr

    # Symbol lookup
    if isinstance(expr, Symbol):
        return env.lookup(expr.name)

    # List expression
    if isinstance(expr, list):
        if len(expr) == 0:
            return NIL

        first = expr[0]

        # Special forms
        if isinstance(first, Symbol):
            if first.name == 'define':
                return eval_define(expr, env)
            elif first.name == 'lambda':
                return eval_lambda(expr, env)
            elif first.name == 'if':
                return eval_if(expr, env)
            elif first.name == 'quote':
                return eval_quote(expr, env)
            elif first.name == 'cond':
                return eval_cond(expr, env)

        # Function application
        proc = eval_expr(first, env)
        if not isinstance(proc, Procedure):
            raise TypeError(f"Not a procedure: {proc}")

        args = [eval_expr(arg, env) for arg in expr[1:]]
        return proc.call(args)

    raise LispError(f"Unknown expression type: {expr}")


def eval_define(expr: List[Any], env: Environment) -> Any:
    """Evaluate a define form: (define name value) or (define (name params...) body)."""
    if len(expr) < 3:
        raise SyntaxError("define: requires at least 2 arguments")

    second = expr[1]
    if isinstance(second, Symbol):
        # (define name value)
        name = second.name
        value = eval_expr(expr[2], env)
        env.define(name, value)
        return None
    elif isinstance(second, list):
        # (define (name params...) body) - shorthand for function
        if len(second) == 0:
            raise SyntaxError("define: invalid function definition")
        name = second[0]
        if not isinstance(name, Symbol):
            raise SyntaxError("define: function name must be a symbol")
        params = []
        for p in second[1:]:
            if not isinstance(p, Symbol):
                raise SyntaxError("define: parameters must be symbols")
            params.append(p.name)
        body = [Symbol('begin')] + expr[2:] if len(expr) > 3 else expr[2]
        if len(expr) == 3:
            body = expr[2]
        else:
            body = [Symbol('begin')] + expr[2:]
        lambda_expr = [Symbol('lambda'), [Symbol(p) for p in params], body]
        value = eval_lambda(lambda_expr, env)
        env.define(name.name, value)
        return None
    else:
        raise SyntaxError("define: invalid syntax")


def eval_lambda(expr: List[Any], env: Environment) -> Procedure:
    """Evaluate a lambda form: (lambda (params...) body)."""
    if len(expr) < 3:
        raise SyntaxError("lambda: requires parameter list and body")

    params_expr = expr[1]
    if not isinstance(params_expr, list):
        raise SyntaxError("lambda: parameters must be a list")

    params = []
    for p in params_expr:
        if not isinstance(p, Symbol):
            raise SyntaxError("lambda: parameters must be symbols")
        params.append(p.name)

    body = expr[2] if len(expr) == 3 else [Symbol('begin')] + expr[2:]

    return Procedure(
        name="lambda",
        params=params,
        body=body,
        env=env
    )


def eval_if(expr: List[Any], env: Environment) -> Any:
    """Evaluate an if form: (if condition then else?)."""
    if len(expr) not in (3, 4):
        raise SyntaxError("if: requires condition, then-branch, and optional else-branch")

    condition = eval_expr(expr[1], env)
    if condition is not False:
        return eval_expr(expr[2], env)
    elif len(expr) == 4:
        return eval_expr(expr[3], env)
    else:
        return None


def eval_quote(expr: List[Any], env: Environment) -> Any:
    """Evaluate a quote form: (quote expr)."""
    if len(expr) != 2:
        raise SyntaxError("quote: requires exactly 1 argument")
    return expr[1]


def eval_cond(expr: List[Any], env: Environment) -> Any:
    """Evaluate a cond form: (cond (test expr)... [(else expr)])."""
    if len(expr) < 2:
        raise SyntaxError("cond: requires at least one clause")

    for clause in expr[1:]:
        if not isinstance(clause, list):
            raise SyntaxError("cond: clauses must be lists")
        if len(clause) < 2:
            raise SyntaxError("cond: each clause must have at least 2 elements")

        test = clause[0]
        if isinstance(test, Symbol) and test.name == 'else':
            result = None
            for e in clause[1:]:
                result = eval_expr(e, env)
            return result

        test_val = eval_expr(test, env)
        if test_val is not False:
            result = None
            for e in clause[1:]:
                result = eval_expr(e, env)
            return result

    return None


# ============================
# REPL Helpers
# ============================
def run(source: str, env: Optional[Environment] = None) -> Any:
    """Run LISP source code and return the last expression's value."""
    tokens = tokenize(source)
    expressions = parse(tokens)
    if env is None:
        env = setup_global_env()
    result = None
    for expr in expressions:
        result = eval_expr(expr, env)
    return result


def lisp_to_py(val: Any) -> Any:
    """Convert LISP value to Python value for easier comparison."""
    if val is NIL:
        return []
    if isinstance(val, Symbol):
        return val.name
    if isinstance(val, Cons):
        result = []
        current = val
        while isinstance(current, Cons):
            result.append(lisp_to_py(current.car))
            current = current.cdr
        if current is not NIL:
            # Improper list
            result.append(Symbol('.'))
            result.append(lisp_to_py(current))
        return result
    if isinstance(val, list):
        return [lisp_to_py(v) for v in val]
    return val


# ============================
# Tests
# ============================
def run_tests():
    """Run all test cases and report results."""
    tests_passed = 0
    tests_failed = 0

    def check(name: str, source: str, expected: Any, env: Optional[Environment] = None):
        nonlocal tests_passed, tests_failed
        try:
            if env is None:
                env = setup_global_env()
            result = run(source, env)
            py_result = lisp_to_py(result)
            if py_result == expected:
                print(f"  PASS: {name}")
                tests_passed += 1
                return True, env
            else:
                print(f"  FAIL: {name}")
                print(f"        Expected: {expected}")
                print(f"        Got:      {py_result}")
                tests_failed += 1
                return False, env
        except Exception as e:
            print(f"  FAIL: {name}")
            print(f"        Error: {type(e).__name__}: {e}")
            tests_failed += 1
            return False, env

    def check_error(name: str, source: str, expected_error_type: type):
        nonlocal tests_passed, tests_failed
        try:
            env = setup_global_env()
            run(source, env)
            print(f"  FAIL: {name}")
            print(f"        Expected {expected_error_type.__name__}, but no error was raised")
            tests_failed += 1
            return False
        except Exception as e:
            if isinstance(e, expected_error_type):
                print(f"  PASS: {name}")
                tests_passed += 1
                return True
            else:
                print(f"  FAIL: {name}")
                print(f"        Expected {expected_error_type.__name__}, got {type(e).__name__}: {e}")
                tests_failed += 1
                return False

    print("Running LISP interpreter tests...")
    print()

    # Test 1: (+ 1 2) => 3
    env = None
    ok, env = check("Addition: (+ 1 2)", "(+ 1 2)", 3)

    # Test 2: (* (+ 1 2) (- 5 2)) => 9
    ok, _ = check("Nested arithmetic", "(* (+ 1 2) (- 5 2))", 9)

    # Test 3: (define x 10), (+ x 5) => 15
    env = setup_global_env()
    ok, env = check("Define variable", "(define x 10)", None, env)
    ok, env = check("Use variable", "(+ x 5)", 15, env)

    # Test 4: factorial 5 => 120
    factorial_src = """
    (define factorial
      (lambda (n)
        (if (= n 0)
            1
            (* n (factorial (- n 1))))))
    (factorial 5)
    """
    ok, _ = check("Recursion: factorial 5", factorial_src, 120)

    # Test 5: lambda square 7 => 49
    square_src = """
    (define square (lambda (x) (* x x)))
    (square 7)
    """
    ok, _ = check("Lambda: square 7", square_src, 49)

    # Test 6: cons/car/cdr list ops
    env = setup_global_env()
    ok, env = check("car", "(car (cons 1 2))", 1, env)
    ok, env = check("cdr", "(cdr (cons 1 2))", 2, env)
    ok, env = check("list", "(list 1 2 3)", [1, 2, 3], env)

    # Test 7: quote
    ok, _ = check("quote", "(quote (1 2 3))", [1, 2, 3])
    ok, _ = check("quote shorthand", "'(a b c)", ['a', 'b', 'c'])

    # Test 8: nested scopes (foo 3 => 13, x still 5)
    scope_src = """
    (define x 5)
    (define foo
      (lambda (x)
        (+ x 10)))
    (foo 3)
    """
    env = setup_global_env()
    ok, env = check("Nested scopes: (foo 3)", scope_src, 13, env)
    # x should still be 5 in global scope
    ok, env = check("Nested scopes: x still 5", "x", 5, env)

    # Test 9: cond
    cond_src = """
    (define grade
      (lambda (score)
        (cond ((> score 90) 'A)
              ((> score 80) 'B)
              ((> score 70) 'C)
              (else 'F))))
    (grade 85)
    """
    ok, _ = check("cond", cond_src, 'B')

    # Test 10: error - too few args
    check_error("Error: too few args", "(= 1)", ArgumentError)

    # Test 11: error - undefined symbol
    check_error("Error: undefined symbol", "(+ x 5)", UndefinedSymbolError)

    print()
    print(f"Results: {tests_passed} passed, {tests_failed} failed")
    print(f"Total:   {tests_passed + tests_failed}")
    return tests_failed == 0


# ============================
# Main
# ============================
if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
