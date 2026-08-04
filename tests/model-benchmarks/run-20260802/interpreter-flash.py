#!/usr/bin/env python3
"""Minimal LISP interpreter in Python with lexical scoping."""


class LispError(Exception):
    """Base class for LISP interpreter errors."""
    pass


class ParseError(LispError):
    """Error during parsing."""
    pass


class RuntimeError(LispError):
    """Error during evaluation."""
    pass


class Symbol:
    """Represents a LISP symbol."""
    __slots__ = ('name',)

    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        return isinstance(other, Symbol) and self.name == other.name

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return self.name


class Env:
    """Environment with lexical scoping."""

    def __init__(self, parent=None, bindings=None):
        self.parent = parent
        self.bindings = bindings or {}

    def define(self, name, value):
        """Define a new binding in this environment."""
        self.bindings[name] = value

    def set(self, name, value):
        """Set an existing binding (searches up the chain)."""
        env = self._find_env(name)
        if env is None:
            raise RuntimeError(f"undefined symbol: {name}")
        env.bindings[name] = value

    def lookup(self, name):
        """Look up a symbol, searching up the parent chain."""
        env = self._find_env(name)
        if env is None:
            raise RuntimeError(f"undefined symbol: {name}")
        return env.bindings[name]

    def _find_env(self, name):
        """Find the environment containing the given name."""
        if name in self.bindings:
            return self
        if self.parent is not None:
            return self.parent._find_env(name)
        return None

    def extend(self, names, values):
        """Create a new child environment with the given bindings."""
        new_env = Env(parent=self)
        for name, value in zip(names, values):
            new_env.define(name, value)
        return new_env


class Procedure:
    """A user-defined LISP procedure (lambda)."""

    def __init__(self, params, body, env):
        self.params = params
        self.body = body
        self.env = env

    def __call__(self, *args):
        if len(args) != len(self.params):
            raise RuntimeError(
                f"too few arguments" if len(args) < len(self.params)
                else f"too many arguments"
            )
        new_env = self.env.extend(self.params, args)
        return evaluate(self.body, new_env)


def tokenize(source):
    """Convert a string into a list of tokens."""
    tokens = []
    i = 0
    while i < len(source):
        ch = source[i]
        if ch.isspace():
            i += 1
        elif ch == ';':
            # Skip comment to end of line
            while i < len(source) and source[i] != '\n':
                i += 1
        elif ch in '()':
            tokens.append(ch)
            i += 1
        elif ch == "'":
            tokens.append("'")
            i += 1
        elif ch == '#':
            # Boolean literals #t and #f
            if i + 1 < len(source) and source[i + 1] in 'tfTF':
                tokens.append(source[i:i + 2].lower())
                i += 2
            else:
                raise ParseError(f"invalid boolean literal at position {i}")
        else:
            # Read atom (number, symbol, or operator)
            start = i
            while i < len(source) and source[i] not in '()\'" \t\n\r;':
                i += 1
            token = source[start:i]
            if token:
                tokens.append(token)
    return tokens


def parse(tokens):
    """Parse tokens into a LISP AST."""
    if not tokens:
        raise ParseError("unexpected end of input")

    token = tokens.pop(0)

    if token == '(':
        lst = []
        while tokens and tokens[0] != ')':
            lst.append(parse(tokens))
        if not tokens:
            raise ParseError("missing closing parenthesis")
        tokens.pop(0)  # remove ')'
        return lst

    if token == ')':
        raise ParseError("unexpected closing parenthesis")

    if token == "'":
        # Quote shorthand: 'expr -> (quote expr)
        expr = parse(tokens)
        return [Symbol('quote'), expr]

    return parse_atom(token)


def parse_atom(token):
    """Parse a single token into an atom."""
    if token == '#t':
        return True
    if token == '#f':
        return False

    # Try integer
    try:
        return int(token)
    except ValueError:
        pass

    # It's a symbol
    return Symbol(token)


def make_global_env():
    """Create the global environment with built-in functions."""
    env = Env()

    # Arithmetic
    def add(*args):
        if not args:
            raise RuntimeError("+ requires at least one argument")
        return sum(args)

    def sub(x, *args):
        if not args:
            return -x
        return x - sum(args)

    def mul(*args):
        if not args:
            raise RuntimeError("* requires at least one argument")
        result = 1
        for a in args:
            result *= a
        return result

    def div(x, *args):
        if not args:
            raise RuntimeError("/ requires at least one argument")
        result = x
        for a in args:
            result //= a
        return result

    # Comparison
    def eq(*args):
        if len(args) < 2:
            raise RuntimeError("= requires at least 2 arguments")
        return all(args[i] == args[i + 1] for i in range(len(args) - 1))

    def lt(*args):
        if len(args) < 2:
            raise RuntimeError("< requires at least 2 arguments")
        return all(args[i] < args[i + 1] for i in range(len(args) - 1))

    def gt(*args):
        if len(args) < 2:
            raise RuntimeError("> requires at least 2 arguments")
        return all(args[i] > args[i + 1] for i in range(len(args) - 1))

    # List operations
    def lisp_cons(x, y):
        if isinstance(y, list):
            return [x] + y
        raise RuntimeError("cons second argument must be a list")

    def lisp_car(lst):
        if isinstance(lst, list) and lst:
            return lst[0]
        raise RuntimeError("car requires a non-empty list")

    def lisp_cdr(lst):
        if isinstance(lst, list) and lst:
            return lst[1:]
        raise RuntimeError("cdr requires a non-empty list")

    def lisp_list(*args):
        return list(args)

    def lisp_null(arg):
        return isinstance(arg, list) and len(arg) == 0

    def lisp_number(arg):
        return isinstance(arg, int)

    def lisp_symbol(arg):
        return isinstance(arg, Symbol)

    def lisp_listp(arg):
        return isinstance(arg, list)

    env.define('+', add)
    env.define('-', sub)
    env.define('*', mul)
    env.define('/', div)
    env.define('=', eq)
    env.define('<', lt)
    env.define('>', gt)
    env.define('cons', lisp_cons)
    env.define('car', lisp_car)
    env.define('cdr', lisp_cdr)
    env.define('list', lisp_list)
    env.define('null?', lisp_null)
    env.define('number?', lisp_number)
    env.define('symbol?', lisp_symbol)
    env.define('list?', lisp_listp)

    return env


def evaluate(expr, env):
    """Evaluate a LISP expression in the given environment."""

    # Self-evaluating atoms
    if isinstance(expr, int):
        return expr
    if isinstance(expr, bool):
        return expr

    # Symbol lookup
    if isinstance(expr, Symbol):
        return env.lookup(expr.name)

    # Empty list
    if isinstance(expr, list) and len(expr) == 0:
        return expr

    # Special forms
    if isinstance(expr, list):
        if len(expr) == 0:
            return expr

        first = expr[0]

        # (quote expr)
        if first == Symbol('quote'):
            if len(expr) != 2:
                raise RuntimeError("quote requires exactly 1 argument")
            return expr[1]

        # (if condition then else?)
        if first == Symbol('if'):
            if len(expr) < 3 or len(expr) > 4:
                raise RuntimeError("if requires 2 or 3 arguments")
            condition = evaluate(expr[1], env)
            if condition:
                return evaluate(expr[2], env)
            elif len(expr) == 4:
                return evaluate(expr[3], env)
            else:
                return None

        # (define name value) or (define (name args...) body...)
        if first == Symbol('define'):
            if len(expr) < 3:
                raise RuntimeError("define requires at least 2 arguments")

            if isinstance(expr[1], list):
                # Function definition shorthand: (define (name args...) body...)
                name = expr[1][0].name
                params = [p.name for p in expr[1][1:]]
                body = expr[2] if len(expr) == 3 else [Symbol('begin')] + expr[2:]
                proc = Procedure(params, body, env)
                env.define(name, proc)
                return None
            else:
                # Variable definition: (define name value)
                name = expr[1].name if isinstance(expr[1], Symbol) else expr[1]
                value = evaluate(expr[2], env)
                env.define(name, value)
                return None

        # (lambda (params...) body)
        if first == Symbol('lambda'):
            if len(expr) < 3:
                raise RuntimeError("lambda requires at least 2 arguments")
            params = [p.name for p in expr[1]]
            body = expr[2] if len(expr) == 3 else [Symbol('begin')] + expr[2:]
            return Procedure(params, body, env)

        # (cond (condition expr)... [(else expr)])
        if first == Symbol('cond'):
            for clause in expr[1:]:
                if not isinstance(clause, list) or len(clause) < 2:
                    raise RuntimeError("cond clause must be a list with at least 2 elements")
                condition = clause[0]
                if condition == Symbol('else'):
                    return evaluate(clause[1], env)
                if evaluate(condition, env):
                    return evaluate(clause[1], env)
            return None

        # (begin expr...)
        if first == Symbol('begin'):
            result = None
            for e in expr[1:]:
                result = evaluate(e, env)
            return result

        # Function application
        func = evaluate(first, env)
        args = [evaluate(arg, env) for arg in expr[1:]]

        if callable(func):
            return func(*args)
        else:
            raise RuntimeError(f"not a procedure: {func}")

    return expr


def run(source, env=None):
    """Parse and evaluate a LISP source string."""
    if env is None:
        env = make_global_env()
    tokens = tokenize(source)
    results = []
    while tokens:
        ast = parse(tokens)
        results.append(evaluate(ast, env))
    return results[-1] if results else None


def run_multiple(source, env=None):
    """Parse and evaluate multiple expressions, returning all results."""
    if env is None:
        env = make_global_env()
    tokens = tokenize(source)
    results = []
    while tokens:
        ast = parse(tokens)
        results.append(evaluate(ast, env))
    return results


def to_string(value):
    """Convert a LISP value to a readable string."""
    if isinstance(value, bool):
        return '#t' if value else '#f'
    if isinstance(value, list):
        return '(' + ' '.join(to_string(v) for v in value) + ')'
    if isinstance(value, Symbol):
        return value.name
    if value is None:
        return '()'
    return str(value)


def run_tests():
    """Run the test suite and report results."""
    tests = [
        # (description, source, expected_or_error)
        ("Test 1: Basic addition",
         "(+ 1 2)", 3),

        ("Test 2: Nested arithmetic",
         "(* (+ 1 2) (- 5 2))", 9),

        ("Test 3: Define and use variable",
         "(define x 10)\n(+ x 5)", 15),

        ("Test 4: Recursive factorial",
         "(define (factorial n)\n  (if (= n 0)\n      1\n      (* n (factorial (- n 1)))))\n(factorial 5)", 120),

        ("Test 5: Lambda",
         "(define square (lambda (x) (* x x)))\n(square 7)", 49),

        ("Test 6: cons list building",
         "(cons 1 (cons 2 (cons 3 '())))", [1, 2, 3]),

        ("Test 7: car",
         "(car (list 1 2 3))", 1),

        ("Test 8: cdr",
         "(cdr (list 1 2 3))", [2, 3]),

        ("Test 9: quote expression",
         "(quote (+ 1 2))", [Symbol('+'), 1, 2]),

        ("Test 10: quote list",
         "(quote (a b c))", [Symbol('a'), Symbol('b'), Symbol('c')]),

        ("Test 11: Nested scopes",
         "(define x 5)\n(define (foo x) (+ x 10))\n(foo 3)\nx", [None, None, 13, 5]),

        ("Test 12: cond",
         "(cond ((> 5 3) 'yes) (else 'no))", Symbol('yes')),

        ("Test 13: Too few arguments",
         "(define (factorial n)\n  (if (= n 0)\n      1\n      (* n (factorial (- n 1)))))\n(factorial)", RuntimeError),

        ("Test 14: Undefined symbol",
         "(undefined 1)", RuntimeError),
    ]

    passed = 0
    failed = 0

    print("=" * 60)
    print("LISP Interpreter Test Suite")
    print("=" * 60)

    for i, (desc, source, expected) in enumerate(tests, 1):
        print(f"\n{desc}")
        print(f"  Source: {source.replace(chr(10), ' ')}")

        try:
            if i == 11:
                # Test 11: multiple expressions, check each result
                results = run_multiple(source)
                if results == expected:
                    print(f"  PASS -> {results}")
                    passed += 1
                else:
                    print(f"  FAIL -> expected {expected}, got {results}")
                    failed += 1
            elif i in (13, 14):
                # Error tests
                try:
                    result = run(source)
                    print(f"  FAIL -> expected {expected.__name__}, got {to_string(result)}")
                    failed += 1
                except RuntimeError as e:
                    print(f"  PASS -> Error: {e}")
                    passed += 1
            else:
                result = run(source)
                # Compare with expected
                match = False
                if isinstance(expected, list):
                    match = (result == expected)
                elif isinstance(expected, Symbol):
                    match = (isinstance(result, Symbol) and result.name == expected.name)
                else:
                    match = (result == expected)

                if match:
                    print(f"  PASS -> {to_string(result)}")
                    passed += 1
                else:
                    print(f"  FAIL -> expected {to_string(expected)}, got {to_string(result)}")
                    failed += 1
        except Exception as e:
            if isinstance(expected, type) and issubclass(expected, Exception):
                print(f"  PASS -> Error: {e}")
                passed += 1
            else:
                print(f"  FAIL -> unexpected error: {e}")
                failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
