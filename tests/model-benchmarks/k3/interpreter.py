"""Minimal LISP interpreter in Python."""

class LispError(Exception):
    """Base exception for LISP runtime errors."""
    pass


class Environment:
    """Nested environment with lexical scoping."""

    def __init__(self, parent=None):
        self.bindings = {}
        self.parent = parent

    def define(self, name, value):
        self.bindings[name] = value

    def lookup(self, name):
        if name in self.bindings:
            return self.bindings[name]
        if self.parent is not None:
            return self.parent.lookup(name)
        raise LispError(f"undefined symbol: {name}")

    def extend(self, params, args):
        env = Environment(self)
        for param, arg in zip(params, args):
            env.define(param, arg)
        return env


class Procedure:
    """User-defined lambda procedure."""

    def __init__(self, params, body, env):
        self.params = params
        self.body = body
        self.env = env

    def __call__(self, args):
        if len(args) != len(self.params):
            if len(args) < len(self.params):
                raise LispError("too few arguments")
            else:
                raise LispError("too many arguments")
        new_env = self.env.extend(self.params, args)
        return evaluate(self.body, new_env)


def tokenize(source):
    """Convert source string into a list of tokens."""
    tokens = []
    i = 0
    while i < len(source):
        c = source[i]
        if c in '()':
            tokens.append(c)
            i += 1
        elif c in ' \t\n\r':
            i += 1
        elif c == ';':
            # Skip comments until end of line
            while i < len(source) and source[i] != '\n':
                i += 1
        elif c == "'":
            tokens.append("'")
            i += 1
        elif c == '#':
            if i + 1 < len(source) and source[i + 1] in 'tf':
                tokens.append(source[i:i + 2])
                i += 2
            else:
                raise LispError(f"invalid token at position {i}")
        else:
            start = i
            while i < len(source) and source[i] not in ' \t\n\r()':
                i += 1
            tokens.append(source[start:i])
    return tokens


def parse(tokens):
    """Convert tokens into LISP expressions (lists of nested atoms)."""

    def parse_expr(i):
        if i >= len(tokens):
            raise LispError("unexpected end of input")
        token = tokens[i]
        if token == '(':
            i += 1
            exprs = []
            while i < len(tokens) and tokens[i] != ')':
                expr, i = parse_expr(i)
                exprs.append(expr)
            if i >= len(tokens):
                raise LispError("missing closing parenthesis")
            i += 1  # skip ')'
            return exprs, i
        elif token == ')':
            raise LispError("unexpected closing parenthesis")
        elif token == "'":
            expr, i = parse_expr(i + 1)
            return ['quote', expr], i
        elif token == '#t':
            return True, i + 1
        elif token == '#f':
            return False, i + 1
        else:
            try:
                return int(token), i + 1
            except ValueError:
                return token, i + 1

    expressions = []
    i = 0
    while i < len(tokens):
        expr, i = parse_expr(i)
        expressions.append(expr)
    return expressions


def evaluate(expr, env):
    """Evaluate an expression in an environment."""
    if isinstance(expr, int):
        return expr
    elif isinstance(expr, bool):
        return expr
    elif isinstance(expr, str):
        return env.lookup(expr)
    elif isinstance(expr, list):
        if len(expr) == 0:
            return expr
        op = expr[0]

        if op == 'define':
            if len(expr) < 3:
                raise LispError("invalid define form")
            if isinstance(expr[1], list):
                # (define (name args...) body ...)
                name = expr[1][0]
                params = expr[1][1:]
                if len(expr) == 3:
                    body = expr[2]
                elif len(expr) > 3:
                    body = ['begin'] + expr[2:]
                else:
                    raise LispError("invalid define form")
                env.define(name, Procedure(params, body, env))
                return None
            else:
                # (define name value)
                name = expr[1]
                value = evaluate(expr[2], env)
                env.define(name, value)
                return value

        elif op == 'lambda':
            if len(expr) < 3:
                raise LispError("invalid lambda form")
            params = expr[1]
            if len(expr) == 3:
                body = expr[2]
            elif len(expr) > 3:
                body = ['begin'] + expr[2:]
            else:
                raise LispError("invalid lambda form")
            return Procedure(params, body, env)

        elif op == 'if':
            if len(expr) != 4:
                raise LispError("invalid if form")
            condition = evaluate(expr[1], env)
            if condition:
                return evaluate(expr[2], env)
            else:
                return evaluate(expr[3], env)

        elif op == 'quote':
            if len(expr) != 2:
                raise LispError("invalid quote form")
            return expr[1]

        elif op == 'cond':
            if len(expr) < 2:
                raise LispError("invalid cond form")
            for i, clause in enumerate(expr[1:]):
                if not isinstance(clause, list) or len(clause) < 2:
                    raise LispError("invalid cond clause")
                if clause[0] == 'else':
                    if i != len(expr[1:]) - 1:
                        raise LispError("else must be last clause in cond")
                    return evaluate(clause[1], env)
                test = evaluate(clause[0], env)
                if test:
                    return evaluate(clause[1], env)
            return None

        elif op == 'begin':
            result = None
            for e in expr[1:]:
                result = evaluate(e, env)
            return result

        else:
            # Function application
            func = evaluate(op, env)
            args = [evaluate(arg, env) for arg in expr[1:]]
            if isinstance(func, Procedure):
                return func(args)
            elif callable(func):
                return func(args)
            else:
                raise LispError(f"not a procedure: {func}")
    else:
        raise LispError(f"unknown expression type: {type(expr)}")


def make_global_env():
    """Create the global environment with built-in functions."""
    env = Environment()

    def arithmetic(op, init=None, unary=None):
        def f(args):
            if len(args) == 0:
                if init is not None:
                    return init
                raise LispError("too few arguments")
            if len(args) == 1 and unary is not None:
                return unary(args[0])
            result = args[0]
            for arg in args[1:]:
                result = op(result, arg)
            return result
        return f

    def comparison(op):
        def f(args):
            if len(args) != 2:
                raise LispError("too few arguments" if len(args) < 2 else "too many arguments")
            return op(args[0], args[1])
        return f

    def cons(args):
        if len(args) != 2:
            raise LispError("too few arguments" if len(args) < 2 else "too many arguments")
        if isinstance(args[1], list):
            return [args[0]] + args[1]
        return [args[0], args[1]]

    def car(args):
        if len(args) != 1:
            raise LispError("too few arguments" if len(args) < 1 else "too many arguments")
        if not isinstance(args[0], list) or len(args[0]) == 0:
            raise LispError("car requires non-empty list")
        return args[0][0]

    def cdr(args):
        if len(args) != 1:
            raise LispError("too few arguments" if len(args) < 1 else "too many arguments")
        if not isinstance(args[0], list):
            raise LispError("cdr requires list")
        return args[0][1:]

    def list_fn(args):
        return list(args)

    def null_p(args):
        if len(args) != 1:
            raise LispError("too few arguments" if len(args) < 1 else "too many arguments")
        return isinstance(args[0], list) and len(args[0]) == 0

    def number_p(args):
        if len(args) != 1:
            raise LispError("too few arguments" if len(args) < 1 else "too many arguments")
        return type(args[0]) is int

    def symbol_p(args):
        if len(args) != 1:
            raise LispError("too few arguments" if len(args) < 1 else "too many arguments")
        return isinstance(args[0], str)

    def list_p(args):
        if len(args) != 1:
            raise LispError("too few arguments" if len(args) < 1 else "too many arguments")
        return isinstance(args[0], list)

    env.define('+', arithmetic(lambda a, b: a + b, init=0))
    env.define('-', arithmetic(lambda a, b: a - b, unary=lambda a: -a))
    env.define('*', arithmetic(lambda a, b: a * b, init=1))
    env.define('/', arithmetic(lambda a, b: a // b))
    env.define('=', comparison(lambda a, b: a == b))
    env.define('<', comparison(lambda a, b: a < b))
    env.define('>', comparison(lambda a, b: a > b))
    env.define('cons', cons)
    env.define('car', car)
    env.define('cdr', cdr)
    env.define('list', list_fn)
    env.define('null?', null_p)
    env.define('number?', number_p)
    env.define('symbol?', symbol_p)
    env.define('list?', list_p)

    return env


def run(source):
    """Evaluate a source string and return the result of the last expression."""
    tokens = tokenize(source)
    expressions = parse(tokens)
    env = make_global_env()
    result = None
    for expr in expressions:
        result = evaluate(expr, env)
    return result


def run_tests():
    """Run all test cases and print pass/fail results."""
    passed = 0
    failed = 0

    def check(name, source, expected):
        nonlocal passed, failed
        try:
            result = run(source)
            if result == expected:
                print(f"PASS: {name}")
                passed += 1
            else:
                print(f"FAIL: {name}")
                print(f"  Expected: {expected}")
                print(f"  Got: {result}")
                failed += 1
        except Exception as e:
            print(f"FAIL: {name}")
            print(f"  Error: {e}")
            failed += 1

    def check_error(name, source, expected_error):
        nonlocal passed, failed
        try:
            result = run(source)
            print(f"FAIL: {name}")
            print(f"  Expected error containing '{expected_error}', got: {result}")
            failed += 1
        except Exception as e:
            if expected_error in str(e):
                print(f"PASS: {name} (Error: {e})")
                passed += 1
            else:
                print(f"FAIL: {name}")
                print(f"  Expected error containing '{expected_error}', got: {e}")
                failed += 1

    # Basic arithmetic
    check("(+ 1 2)", "(+ 1 2)", 3)
    check("nested arithmetic", "(* (+ 1 2) (- 5 2))", 9)

    # Variables
    check("variables", "(define x 10)\n(+ x 5)", 15)

    # Factorial
    check("factorial",
          "(define (factorial n) (if (= n 0) 1 (* n (factorial (- n 1)))))\n(factorial 5)",
          120)

    # Lambda
    check("lambda",
          "(define square (lambda (x) (* x x)))\n(square 7)",
          49)

    # Lists
    check("cons list", "(cons 1 (cons 2 (cons 3 '())))", [1, 2, 3])
    check("car", "(define lst (list 1 2 3))\n(car lst)", 1)
    check("cdr", "(define lst (list 1 2 3))\n(cdr lst)", [2, 3])

    # Quoting
    check("quote", "(quote (+ 1 2))", ['+', 1, 2])

    # Nested scopes
    check("nested scopes: foo(3)",
          "(define x 5)\n(define (foo x) (+ x 10))\n(foo 3)",
          13)
    check("nested scopes: x still 5",
          "(define x 5)\n(define (foo x) (+ x 10))\n(foo 3)\nx",
          5)

    # Cond
    check("cond", "(cond ((> 5 3) 'yes) (else 'no))", 'yes')

    # Error handling
    check_error("too few arguments",
                "(define (factorial n) (if (= n 0) 1 (* n (factorial (- n 1)))))\n(factorial)",
                "too few arguments")
    check_error("undefined symbol", "(undefined 1)", "undefined symbol")

    print(f"\n{passed} passed, {failed} failed")


if __name__ == '__main__':
    run_tests()
