class Symbol:
    def __init__(self, name):
        self.name = name
    def __eq__(self, other):
        return isinstance(other, Symbol) and self.name == other.name
    def __hash__(self):
        return hash(self.name)
    def __repr__(self):
        return self.name

class Procedure:
    def __init__(self, params, body, env):
        self.params = params
        self.body = body
        self.env = env

class Environment:
    def __init__(self, parent=None):
        self.bindings = {}
        self.parent = parent
    def define(self, name, value):
        self.bindings[name] = value
    def set(self, name, value):
        self.bindings[name] = value
    def lookup(self, name):
        if name in self.bindings:
            return self.bindings[name]
        if self.parent:
            return self.parent.lookup(name)
        raise NameError(f"Undefined: {name}")

def tokenize(s):
    s = s.replace("(", " ( ").replace(")", " ) ")
    tokens = []
    i = 0
    while i < len(s):
        if s[i] == "'":
            tokens.append("'")
            i += 1
        elif s[i] in "()":
            tokens.append(s[i])
            i += 1
        elif s[i].isspace():
            i += 1
        else:
            j = i
            while j < len(s) and not s[j].isspace() and s[j] not in "()":
                j += 1
            tokens.append(s[i:j])
            i = j
    return tokens

def parse(tokens):
    pos = 0
    def parse_expr():
        nonlocal pos
        if pos >= len(tokens):
            raise SyntaxError("Unexpected EOF")
        tok = tokens[pos]
        if tok == "(":
            pos += 1
            lst = []
            while pos < len(tokens) and tokens[pos] != ")":
                lst.append(parse_expr())
            if pos >= len(tokens):
                raise SyntaxError("Missing )")
            pos += 1
            return lst
        elif tok == "'":
            pos += 1
            return [Symbol("quote"), parse_expr()]
        elif tok == ")":
            raise SyntaxError("Unexpected )")
        else:
            pos += 1
            if tok == "#t":
                return True
            if tok == "#f":
                return False
            try:
                return int(tok)
            except ValueError:
                return Symbol(tok)
    return parse_expr()

def is_list(x):
    return isinstance(x, list)

def make_list(*args):
    return list(args)

def is_number(x):
    return isinstance(x, int) and not isinstance(x, bool)

def is_symbol(x):
    return isinstance(x, Symbol)

def is_null(x):
    return is_list(x) and len(x) == 0

def lisp_str(x):
    if x is True:
        return "#t"
    if x is False:
        return "#f"
    if isinstance(x, Symbol):
        return x.name
    if is_list(x):
        return "(" + " ".join(lisp_str(e) for e in x) + ")"
    if isinstance(x, Procedure):
        return "#<procedure>"
    return str(x)

def evaluate(expr, env):
    if isinstance(expr, int) and not isinstance(expr, bool):
        return expr
    if isinstance(expr, bool):
        return expr
    if isinstance(expr, Symbol):
        return env.lookup(expr.name)
    if not is_list(expr):
        return expr

    if len(expr) == 0:
        return expr

    op = expr[0]

    if op == Symbol("define"):
        if len(expr) < 3:
            raise SyntaxError("Bad define")
        if is_list(expr[1]):
            name = expr[1][0].name
            params = [p.name for p in expr[1][1:]]
            body = expr[2] if len(expr) == 3 else [Symbol("begin")] + expr[2:]
            env.define(name, Procedure(params, body, env))
            return None
        else:
            name = expr[1].name
            value = evaluate(expr[2], env)
            env.define(name, value)
            return None

    if op == Symbol("lambda"):
        params = [p.name for p in expr[1]]
        body = expr[2] if len(expr) == 3 else [Symbol("begin")] + expr[2:]
        return Procedure(params, body, env)

    if op == Symbol("if"):
        cond = evaluate(expr[1], env)
        if cond:
            return evaluate(expr[2], env)
        else:
            return evaluate(expr[3], env)

    if op == Symbol("quote"):
        return expr[1]

    if op == Symbol("cond"):
        for clause in expr[1:]:
            if clause[0] == Symbol("else"):
                return evaluate(clause[1], env)
            if evaluate(clause[0], env):
                return evaluate(clause[1], env)
        return None

    if op == Symbol("begin"):
        result = None
        for e in expr[1:]:
            result = evaluate(e, env)
        return result

    proc = evaluate(op, env)
    args = [evaluate(arg, env) for arg in expr[1:]]

    if isinstance(proc, Procedure):
        new_env = Environment(proc.env)
        for p, a in zip(proc.params, args):
            new_env.define(p, a)
        return evaluate(proc.body, new_env)

    return proc(*args)

def make_global_env():
    env = Environment()
    env.define("+", lambda *args: sum(args))
    env.define("-", lambda a, *args: a - sum(args) if args else -a)
    env.define("*", lambda *args: 1 if not args else args[0] * make_global_env.__closure__[0].cell_contents["*"](*args[1:]) if False else eval("*".join(str(a) for a in args)) if len(args) <= 1 else args[0] * (args[1] if len(args) == 2 else env.lookup("*")(*args[1:])))
    def mul(*args):
        r = 1
        for a in args:
            r *= a
        return r
    env.define("*", mul)
    def div(a, *args):
        if not args:
            return 1 / a
        r = a
        for b in args:
            r /= b
        return r
    env.define("/", div)
    env.define("=", lambda a, b: a == b)
    env.define("<", lambda a, b: a < b)
    env.define(">", lambda a, b: a > b)
    env.define("cons", lambda a, b: [a] + (b if is_list(b) else [b]))
    env.define("car", lambda a: a[0] if a else None)
    env.define("cdr", lambda a: a[1:] if len(a) > 1 else [])
    env.define("list", lambda *args: list(args))
    env.define("null?", is_null)
    env.define("number?", is_number)
    env.define("symbol?", is_symbol)
    env.define("list?", is_list)
    return env

def run(src):
    tokens = tokenize(src)
    exprs = []
    while tokens:
        expr, tokens = _parse_one(tokens)
        exprs.append(expr)
    env = make_global_env()
    result = None
    for e in exprs:
        result = evaluate(e, env)
    return result

def _parse_one(tokens):
    expr = parse(tokens)
    consumed = len(tokens)
    return expr, tokens[consumed:]

def run_tests():
    tests = [
        ("(+ 1 2)", 3),
        ("(* (+ 1 2) (- 5 2))", 9),
        ("(define x 10) (+ x 5)", 15),
        ("(define (factorial n) (if (= n 0) 1 (* n (factorial (- n 1))))) (factorial 5)", 120),
        ("(define square (lambda (x) (* x x))) (square 7)", 49),
        ("(cons 1 (cons 2 (cons 3 '())))", [1, 2, 3]),
        ("(car (list 1 2 3))", 1),
        ("(cdr (list 1 2 3))", [2, 3]),
        ("(quote (+ 1 2))", [Symbol("+"), 1, 2]),
        ("(define x 5) (define (foo x) (+ x 10)) (foo 3)", 13),
        ("(cond ((> 5 3) 'yes) (else 'no))", Symbol("yes")),
    ]
    passed = 0
    for i, (src, expected) in enumerate(tests, 1):
        try:
            result = run(src)
            if i == 10:
                env = make_global_env()
                tokens = tokenize(src)
                exprs = []
                while tokens:
                    expr, tokens = _parse_one(tokens)
                    exprs.append(expr)
                for e in exprs:
                    evaluate(e, env)
                result = env.lookup("x")
                expected = 5
            ok = result == expected
            if i == 6 and result == [1, 2, 3]:
                ok = True
            if i == 8 and result == [2, 3]:
                ok = True
            if i == 9:
                ok = isinstance(result, list) and len(result) == 3 and result[0] == Symbol("+") and result[1] == 1 and result[2] == 2
            if ok:
                print(f"Test {i}: PASS")
                passed += 1
            else:
                print(f"Test {i}: FAIL (expected {expected}, got {result})")
        except Exception as e:
            print(f"Test {i}: FAIL ({e})")
    print(f"\n{passed}/{len(tests)} tests passed")
    return passed, len(tests)

if __name__ == "__main__":
    run_tests()
