"""
T2-k3-json_parser.py — A JSON parser from scratch.
Implements a tokenizer + recursive-descent parser with meaningful error messages.
"""


class JSONParseError(Exception):
    """Raised when JSON input is malformed."""
    pass


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

class Token:
    def __init__(self, kind, value, pos):
        self.kind = kind   # e.g. 'STRING', 'NUMBER', 'LBRACE', etc.
        self.value = value
        self.pos = pos     # index in source where token starts

    def __repr__(self):
        return f"Token({self.kind!r}, {self.value!r}, pos={self.pos})"


TOKEN_SPEC = [
    ('WHITESPACE', r'[ \t\n\r]+'),
    ('NUMBER',     r'-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+\-]?\d+)?'),
    ('STRING',     r'"(?:[^"\\\x00-\x1f]|\\["\\/bfnrt]|\\u[0-9a-fA-F]{4})*"'),
    ('LBRACE',     r'\{'),
    ('RBRACE',     r'\}'),
    ('LBRACKET',   r'\['),
    ('RBRACKET',   r'\]'),
    ('COLON',      r':'),
    ('COMMA',      r','),
    ('TRUE',       r'true'),
    ('FALSE',      r'false'),
    ('NULL',       r'null'),
]

# Build a single regex for all token types
import re

_token_re = re.compile(
    '|'.join(f'(?P<{name}>{pattern})' for name, pattern in TOKEN_SPEC),
    re.VERBOSE
)


def tokenize(text):
    """Return a list of Tokens (skipping whitespace) or raise JSONParseError."""
    pos = 0
    tokens = []
    while pos < len(text):
        m = _token_re.match(text, pos)
        if not m:
            bad_char = text[pos]
            snippet = text[pos:pos + 20].replace('\n', '\\n')
            raise JSONParseError(
                f"Unexpected character {bad_char!r} at position {pos} (near: {snippet!r})"
            )
        kind = m.lastgroup
        value = m.group()
        if kind != 'WHITESPACE':
            tokens.append(Token(kind, value, pos))
        pos = m.end()

    # Append an EOF sentinel so parser methods can peek safely
    tokens.append(Token('EOF', '', pos))
    return tokens


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def current(self):
        return self.tokens[self.pos]

    def advance(self):
        tok = self.current()
        self.pos += 1
        return tok

    def expect(self, kind, context=""):
        tok = self.current()
        if tok.kind != kind:
            ctx = f" {context}" if context else ""
            raise JSONParseError(
                f"Expected {kind} but got {tok.kind} ({tok.value!r}) at position {tok.pos}.{ctx}"
            )
        return self.advance()

    # -------------------------------------------------------------------
    # Entry point
    # -------------------------------------------------------------------
    def parse(self):
        if self.current().kind == 'EOF':
            raise JSONParseError("Empty JSON input.")
        value = self.parse_value()
        if self.current().kind != 'EOF':
            extra = self.current()
            raise JSONParseError(
                f"Unexpected extra data after valid JSON: {extra.kind} ({extra.value!r}) at position {extra.pos}."
            )
        return value

    # -------------------------------------------------------------------
    # Value dispatch
    # -------------------------------------------------------------------
    def parse_value(self):
        tok = self.current()
        if tok.kind == 'STRING':
            return self.parse_string_literal()
        if tok.kind == 'NUMBER':
            return self.parse_number_literal()
        if tok.kind == 'TRUE':
            self.advance()
            return True
        if tok.kind == 'FALSE':
            self.advance()
            return False
        if tok.kind == 'NULL':
            self.advance()
            return None
        if tok.kind == 'LBRACE':
            return self.parse_object()
        if tok.kind == 'LBRACKET':
            return self.parse_array()

        raise JSONParseError(
            f"Unexpected token {tok.kind} ({tok.value!r}) at position {tok.pos} — expected a JSON value."
        )

    # -------------------------------------------------------------------
    # String
    # -------------------------------------------------------------------
    def parse_string_literal(self):
        tok = self.advance()   # consume STRING token
        raw = tok.value
        # raw includes surrounding quotes; strip them
        content = raw[1:-1]
        return _unescape(content)

    # -------------------------------------------------------------------
    # Number
    # -------------------------------------------------------------------
    def parse_number_literal(self):
        tok = self.advance()
        text = tok.value
        if '.' in text or 'e' in text or 'E' in text:
            return float(text)
        return int(text)

    # -------------------------------------------------------------------
    # Object
    # -------------------------------------------------------------------
    def parse_object(self):
        self.expect('LBRACE')
        obj = {}

        # Empty object?
        if self.current().kind == 'RBRACE':
            self.advance()
            return obj

        while True:
            key_tok = self.current()
            if key_tok.kind != 'STRING':
                raise JSONParseError(
                    f"Object key must be a string, got {key_tok.kind} ({key_tok.value!r}) at position {key_tok.pos}."
                )
            key = self.parse_string_literal()

            self.expect('COLON', context="after object key")

            value = self.parse_value()
            obj[key] = value

            tok = self.current()
            if tok.kind == 'COMMA':
                self.advance()
                # After a comma, the next token must be a string key or RBRACE (trailing comma error)
                if self.current().kind == 'RBRACE':
                    raise JSONParseError(
                        f"Trailing comma in object at position {tok.pos}."
                    )
                continue
            elif tok.kind == 'RBRACE':
                self.advance()
                break
            else:
                raise JSONParseError(
                    f"Expected ',' or '}}' in object, got {tok.kind} ({tok.value!r}) at position {tok.pos}."
                )

        return obj

    # -------------------------------------------------------------------
    # Array
    # -------------------------------------------------------------------
    def parse_array(self):
        self.expect('LBRACKET')
        arr = []

        # Empty array?
        if self.current().kind == 'RBRACKET':
            self.advance()
            return arr

        while True:
            value = self.parse_value()
            arr.append(value)

            tok = self.current()
            if tok.kind == 'COMMA':
                self.advance()
                if self.current().kind == 'RBRACKET':
                    raise JSONParseError(
                        f"Trailing comma in array at position {tok.pos}."
                    )
                continue
            elif tok.kind == 'RBRACKET':
                self.advance()
                break
            else:
                raise JSONParseError(
                    f"Expected ',' or ']' in array, got {tok.kind} ({tok.value!r}) at position {tok.pos}."
                )

        return arr


# ---------------------------------------------------------------------------
# String unescaping
# ---------------------------------------------------------------------------

_ESCAPE_MAP = {
    '"': '"',
    '\\': '\\',
    '/': '/',
    'b': '\b',
    'f': '\f',
    'n': '\n',
    'r': '\r',
    't': '\t',
}

_unicode_re = re.compile(r'\\u([0-9a-fA-F]{4})')


def _unescape(s):
    """Process escape sequences inside a JSON string body (no surrounding quotes)."""
    result = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == '\\':
            if i + 1 >= len(s):
                raise JSONParseError("Invalid escape at end of string.")
            esc = s[i + 1]
            if esc in _ESCAPE_MAP:
                result.append(_ESCAPE_MAP[esc])
                i += 2
            elif esc == 'u':
                if i + 5 >= len(s):
                    raise JSONParseError("Incomplete unicode escape \\uXXXX.")
                hex_digits = s[i + 2:i + 6]
                try:
                    code_point = int(hex_digits, 16)
                except ValueError:
                    raise JSONParseError(f"Invalid unicode escape \\u{hex_digits}.")
                result.append(chr(code_point))
                i += 6
            else:
                raise JSONParseError(f"Unknown escape sequence \\{esc}.")
        else:
            result.append(ch)
            i += 1
    return ''.join(result)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_json(text):
    """Parse a JSON string and return the corresponding Python object."""
    tokens = tokenize(text)
    parser = Parser(tokens)
    return parser.parse()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def run_tests():
    tests = [
        # (description, input, expected)
        ("integer", "42", 42),
        ("negative float", "-3.14", -3.14),
        ("true", "true", True),
        ("false", "false", False),
        ("null", "null", None),
        ("simple string", '"hello"', "hello"),
        ("array of ints", "[1, 2, 3]", [1, 2, 3]),
        ("empty array", "[]", []),
        ("simple object", '{"a": 1, "b": 2}', {"a": 1, "b": 2}),
        ("empty object", "{}", {}),
        ("nested mixed", '{"x": [1, {"y": 2}]}', {"x": [1, {"y": 2}]}),
        ("array of objects", '[{"a": 1}, {"b": 2}]', [{"a": 1}, {"b": 2}]),
        ("newline escape", '"hello\\nworld"', "hello\nworld"),
        ("quote escape", '"quote: \\\"hi\\\""', 'quote: "hi"'),
    ]

    error_tests = [
        # (description, input, expected_substring_in_error)
        ("unclosed object", '{"a": 1', "Expected ',' or '}'"),
        ("missing colon", '{"a" 1}', "COLON"),
        ("trailing comma object", '{"a": 1,}', "Trailing comma"),
        ("trailing comma array", "[1, 2,]", "Trailing comma"),
    ]

    passed = 0
    failed = 0

    print("=" * 60)
    print("Running parse_json tests")
    print("=" * 60)

    for desc, inp, expected in tests:
        try:
            result = parse_json(inp)
            if result == expected:
                print(f"  PASS  — {desc}")
                passed += 1
            else:
                print(f"  FAIL  — {desc}: expected {expected!r}, got {result!r}")
                failed += 1
        except Exception as e:
            print(f"  FAIL  — {desc}: raised {type(e).__name__}: {e}")
            failed += 1

    for desc, inp, expected_substr in error_tests:
        try:
            result = parse_json(inp)
            print(f"  FAIL  — {desc}: expected error containing {expected_substr!r}, got {result!r}")
            failed += 1
        except JSONParseError as e:
            msg = str(e)
            if expected_substr in msg:
                print(f"  PASS  — {desc} (error: {msg})")
                passed += 1
            else:
                print(f"  FAIL  — {desc}: error missing {expected_substr!r}. Got: {msg}")
                failed += 1
        except Exception as e:
            print(f"  FAIL  — {desc}: unexpected exception {type(e).__name__}: {e}")
            failed += 1

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed out of {passed + failed}")
    print("=" * 60)
    return failed == 0


if __name__ == "__main__":
    import sys
    ok = run_tests()
    sys.exit(0 if ok else 1)
