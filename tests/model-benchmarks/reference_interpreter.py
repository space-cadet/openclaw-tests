#!/usr/bin/env python3
"""
Mini LISP Interpreter - Reference Implementation
For model benchmarking: K2.6 vs K2.7 Code
"""

import re
import time
from typing import Any, Dict, List, Optional, Callable

# ============ DATA TYPES ============

class Symbol:
    def __init__(self, name: str):
        self.name = name
    def __eq__(self, other):
        return isinstance(other, Symbol) and self.name == other.name
    def __repr__(self):
        return self.name
    def __hash__(self):
        return hash(self.name)

class Boolean:
    def __init__(self, value: bool):
        self.value = value
    def __eq__(self, other):
        return isinstance(other, Boolean) and self.value == other.value
    def __repr__(self):
        return "#t" if self.value else "#f"
    def __bool__(self):
        return self.value

class Procedure:
    def __init__(self, params: List[str], body: List[Any], env: 'Environment'):
        self.params = params
        self.body = body
        self.env = env
    def __repr__(self):
        return f"#<procedure ({' '.join(self.params)})>"

# ============ ENVIRONMENT ============

class Environment:
    def __init__(self, parent: Optional['Environment'] = None):
        self.bindings: Dict[str, Any] = {}
        self.parent = parent
    
    def define(self, name: str, value: Any):
        self.bindings[name] = value
    
    def lookup(self, name: str) -> Any:
        if name in self.bindings:
            return self.bindings[name]
        if self.parent:
            return self.parent.lookup(name)
        raise NameError(f"Undefined symbol: {name}")
    
    def set(self, name: str, value: Any):
        if name in self.bindings:
            self.bindings[name] = value
        elif self.parent:
            self.parent.set(name, value)
        else:
            raise NameError(f"Undefined symbol: {name}")

# ============ TOKENIZER ============

TOKEN_PATTERNS = [
    (r'\s+', None),                    # whitespace
    (r';[^\n]*', None),                # comments
    (r'\#t|\#f', 'BOOLEAN'),           # booleans
    (r'-?\d+', 'NUMBER'),              # integers
    (r"'", 'QUOTE'),                   # quote shorthand
    (r'[()]', 'PAREN'),                # parentheses
    (r'[^\s()\';]+', 'SYMBOL'),        # symbols
]

def tokenize(code: str) -> List[tuple]:
    tokens = []
    pos = 0
    while pos < len(code):
        matched = False
        for pattern, type_ in TOKEN_PATTERNS:
            regex = re.compile(pattern)
            match = regex.match(code, pos)
            if match:
                if type_:
                    tokens.append((type_, match.group()))
                pos = match.end()
                matched = True
                break
        if not matched:
            raise SyntaxError(f"Unexpected character at position {pos}: {code[pos:]}")
    return tokens

# ============ PARSER ============

def parse(tokens: List[tuple]) -> List[Any]:
    pos = [0]
    
    def parse_expr() -> Any:
        if pos[0] >= len(tokens):
            raise SyntaxError("Unexpected end of input")
        
        type_, value = tokens[pos[0]]
        pos[0] += 1
        
        if type_ == 'NUMBER':
            return int(value)
        elif type_ == 'BOOLEAN':
            return Boolean(value == '#t')
        elif type_ == 'QUOTE':
            return [Symbol('quote'), parse_expr()]
        elif type_ == 'SYMBOL':
            return Symbol(value)
        elif type_ == 'PAREN' and value == '(':
            lst = []
            while pos[0] < len(tokens) and not (tokens[pos[0]] == ('PAREN', ')')):
                lst.append(parse_expr())
            if pos[0] >= len(tokens):
                raise SyntaxError("Unclosed parenthesis")
            pos[0] += 1  # skip ')'
            return lst
        else:
            raise SyntaxError(f"Unexpected token: {value}")
    
    expressions = []
    while pos[0] < len(tokens):
        expressions.append(parse_expr())
    return expressions

# ============ EVALUATOR ============

def evaluate(expr: Any, env: Environment) -> Any:
    if isinstance(expr, int):
        return expr
    elif isinstance(expr, Boolean):
        return expr
    elif isinstance(expr, Symbol):
        return env.lookup(expr.name)
    elif not isinstance(expr, list):
        return expr
    
    if len(expr) == 0:
        return expr
    
    # Special forms
    first = expr[0]
    if isinstance(first, Symbol):
        if first.name == 'quote':
            if len(expr) != 2:
                raise ValueError("quote requires exactly 1 argument")
            return expr[1]
        
        elif first.name == 'define':
            if len(expr) < 3:
                raise ValueError("define requires at least 2 arguments")
            if isinstance(expr[1], list):  # (define (name args...) body...)
                name = expr[1][0].name
                params = [p.name for p in expr[1][1:]]
                body = expr[2:]
                env.define(name, Procedure(params, body, env))
                return None
            else:  # (define name value)
                name = expr[1].name
                value = evaluate(expr[2], env)
                env.define(name, value)
                return value
        
        elif first.name == 'lambda':
            if len(expr) < 3:
                raise ValueError("lambda requires at least 2 arguments")
            params = [p.name for p in expr[1]]
            body = expr[2:]
            return Procedure(params, body, env)
        
        elif first.name == 'if':
            if len(expr) not in [3, 4]:
                raise ValueError("if requires 2 or 3 arguments")
            condition = evaluate(expr[1], env)
            if condition:  # truthy
                return evaluate(expr[2], env)
            elif len(expr) == 4:
                return evaluate(expr[3], env)
            else:
                return None
        
        elif first.name == 'cond':
            for clause in expr[1:]:
                if not isinstance(clause, list) or len(clause) < 2:
                    raise ValueError("cond clauses must be lists with at least 2 elements")
                test = clause[0]
                if isinstance(test, Symbol) and test.name == 'else':
                    result = None
                    for e in clause[1:]:
                        result = evaluate(e, env)
                    return result
                elif evaluate(test, env):
                    result = None
                    for e in clause[1:]:
                        result = evaluate(e, env)
                    return result
            return None
    
    # Function application
    func = evaluate(first, env)
    args = [evaluate(arg, env) for arg in expr[1:]]
    
    if isinstance(func, Procedure):
        if len(args) != len(func.params):
            raise ValueError(f"Expected {len(func.params)} arguments, got {len(args)}")
        new_env = Environment(func.env)
        for param, arg in zip(func.params, args):
            new_env.define(param, arg)
        result = None
        for body_expr in func.body:
            result = evaluate(body_expr, new_env)
        return result
    elif callable(func):
        return func(*args)
    else:
        raise TypeError(f"Not a function: {func}")

# ============ BUILT-IN FUNCTIONS ============

def make_global_env() -> Environment:
    env = Environment()
    
    # Arithmetic
    env.define('+', lambda *args: sum(args))
    env.define('-', lambda a, *args: a - sum(args) if args else -a)
    env.define('*', lambda *args: 1 if not args else args[0] * (args[1] if len(args) > 1 else 1) if len(args) == 1 else eval('*'.join(map(str, args))))
    env.define('/', lambda a, b: a // b)
    
    # Fix multiplication
    def multiply(*args):
        result = 1
        for a in args:
            result *= a
        return result
    env.define('*', multiply)
    
    # Comparison
    env.define('=', lambda a, b: Boolean(a == b))
    env.define('<', lambda a, b: Boolean(a < b))
    env.define('>', lambda a, b: Boolean(a > b))
    
    # List operations
    env.define('cons', lambda a, b: [a] + b if isinstance(b, list) else [a, b])
    env.define('car', lambda lst: lst[0] if isinstance(lst, list) and len(lst) > 0 else None)
    env.define('cdr', lambda lst: lst[1:] if isinstance(lst, list) and len(lst) > 0 else [])
    env.define('list', lambda *args: list(args))
    
    # Predicates
    env.define('null?', lambda x: Boolean(isinstance(x, list) and len(x) == 0))
    env.define('number?', lambda x: Boolean(isinstance(x, int)))
    env.define('symbol?', lambda x: Boolean(isinstance(x, Symbol)))
    env.define('list?', lambda x: Boolean(isinstance(x, list)))
    
    return env

# ============ REPL & TESTS ============

def run(code: str, env: Optional[Environment] = None) -> Any:
    if env is None:
        env = make_global_env()
    tokens = tokenize(code)
    expressions = parse(tokens)
    result = None
    for expr in expressions:
        result = evaluate(expr, env)
    return result

def run_tests():
    print("=" * 60)
    print("MINI LISP INTERPRETER - TEST SUITE")
    print("=" * 60)
    
    tests = [
        ("(+ 1 2)", 3, "Basic arithmetic"),
        ("(* (+ 1 2) (- 5 2))", 9, "Nested arithmetic"),
        ("(define x 10) (+ x 5)", 15, "Variable definition"),
        ("(define (factorial n) (if (= n 0) 1 (* n (factorial (- n 1))))) (factorial 5)", 120, "Recursion"),
        ("(define square (lambda (x) (* x x))) (square 7)", 49, "Lambda"),
        ("(cons 1 (cons 2 (cons 3 '())))", [1, 2, 3], "List construction"),
        ("(car (list 1 2 3))", 1, "car"),
        ("(cdr (list 1 2 3))", [2, 3], "cdr"),
        ("(quote (+ 1 2))", [Symbol('+'), 1, 2], "Quoting"),
        ("(define x 5) (define (foo x) (+ x 10)) (foo 3)", 13, "Nested scopes"),
        ("(cond ((> 5 3) 'yes) (else 'no))", Symbol('yes'), "Conditional"),
    ]
    
    passed = 0
    total = len(tests)
    
    for i, (code, expected, desc) in enumerate(tests, 1):
        try:
            env = make_global_env()
            result = run(code, env)
            
            # Check scoping test
            if desc == "Nested scopes":
                x_val = env.lookup('x')
                if x_val != 5:
                    print(f"  FAIL: Global x should be 5, got {x_val}")
                    continue
            
            if result == expected:
                print(f"  PASS [{i}/{total}] {desc}")
                passed += 1
            else:
                print(f"  FAIL [{i}/{total}] {desc}")
                print(f"    Expected: {expected}")
                print(f"    Got: {result}")
        except Exception as e:
            print(f"  FAIL [{i}/{total}] {desc}")
            print(f"    Error: {e}")
    
    print("-" * 60)
    print(f"RESULTS: {passed}/{total} tests passed")
    print("=" * 60)
    return passed, total

if __name__ == "__main__":
    start = time.time()
    passed, total = run_tests()
    elapsed = time.time() - start
    print(f"Runtime: {elapsed:.3f}s")
