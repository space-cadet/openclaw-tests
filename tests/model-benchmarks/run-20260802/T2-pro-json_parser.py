#!/usr/bin/env python3
"""
JSON parser from scratch — tokenizer + recursive descent parser.
No json module or ast.literal_eval.
"""

from __future__ import annotations

import re
from typing import Any


class JSONError(Exception):
    """Custom exception for JSON parse errors."""
    pass


class Token:
    """A single lexical token."""
    __slots__ = ("type", "value", "pos")

    def __init__(self, type_: str, value: Any, pos: int):
        self.type = type_
        self.value = value
        self.pos = pos

    def __repr__(self) -> str:
        return f"Token({self.type!r}, {self.value!r}, pos={self.pos})"


class Tokenizer:
    """Convert raw JSON text into a stream of Tokens."""

    # Token patterns (order matters — longer literals before shorter)
    RULES = [
        ("WHITESPACE", re.compile(r"[ \t\n\r]+")),
        ("STRING",     re.compile(r'"([^"\\]|\\.)*"')),
        ("NUMBER",     re.compile(r"-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?")),
        ("TRUE",       re.compile(r"true\b")),
        ("FALSE",      re.compile(r"false\b")),
        ("NULL",       re.compile(r"null\b")),
        ("LBRACE",     re.compile(r"\{")),
        ("RBRACE",     re.compile(r"\}")),
        ("LBRACKET",   re.compile(r"\[")),
        ("RBRACKET",   re.compile(r"\]")),
        ("COLON",      re.compile(r":")),
        ("COMMA",      re.compile(r",")),
    ]

    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.tokens: list[Token] = []
        self._run()

    def _run(self) -> None:
        while self.pos < len(self.text):
            matched = False
            for tok_type, pattern in self.RULES:
                m = pattern.match(self.text, self.pos)
                if m:
                    raw = m.group(0)
                    if tok_type != "WHITESPACE":
                        self.tokens.append(Token(tok_type, raw, self.pos))
                    self.pos += len(raw)
                    matched = True
                    break
            if not matched:
                bad = self.text[self.pos : self.pos + 20]
                raise JSONError(
                    f"Unexpected character {self.text[self.pos]!r} at position {self.pos} "
                    f"(near {bad!r})"
                )


# ---------------------------------------------------------------------------
# Escape handling for strings
# ---------------------------------------------------------------------------
ESCAPE_MAP = {
    '"': '"',
    '\\': '\\',
    '/': '/',
    'b': '\b',
    'f': '\f',
    'n': '\n',
    'r': '\r',
    't': '\t',
}


def _unescape(s: str, offset: int) -> str:
    """Unescape a JSON string value (the characters between the quotes)."""
    result = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == '\\':
            if i + 1 >= len(s):
                raise JSONError(f"Incomplete escape sequence at position {offset + i}")
            esc = s[i + 1]
            if esc in ESCAPE_MAP:
                result.append(ESCAPE_MAP[esc])
                i += 2
            elif esc == 'u':
                if i + 5 >= len(s):
                    raise JSONError(
                        f"Incomplete Unicode escape at position {offset + i}"
                    )
                hex_code = s[i + 2 : i + 6]
                try:
                    code_point = int(hex_code, 16)
                except ValueError:
                    raise JSONError(
                        f"Invalid Unicode escape \\u{hex_code} at position {offset + i}"
                    )
                result.append(chr(code_point))
                i += 6
            else:
                raise JSONError(
                    f"Invalid escape sequence \\{esc!r} at position {offset + i}"
                )
        else:
            result.append(ch)
            i += 1
    return "".join(result)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------
class Parser:
    """Recursive-descent parser over a list of Tokens."""

    def __init__(self, tokens: list[Token], text: str):
        self.tokens = tokens
        self.text = text
        self.pos = 0

    @property
    def current(self) -> Token | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _expect(self, *types: str) -> Token:
        """Consume the current token if it matches one of *types*, else error."""
        tok = self.current
        if tok is None:
            raise JSONError(
                f"Unexpected end of input — expected {self._join_types(types)}"
            )
        if tok.type not in types:
            raise JSONError(
                f"Unexpected token {tok.value!r} ({tok.type}) at position {tok.pos} — "
                f"expected {self._join_types(types)}"
            )
        self.pos += 1
        return tok

    @staticmethod
    def _join_types(types: tuple[str, ...]) -> str:
        return " or ".join(types)

    def parse(self) -> Any:
        if not self.tokens:
            raise JSONError("Empty input — no JSON value found")
        value = self._parse_value()
        if self.current is not None:
            raise JSONError(
                f"Unexpected trailing token {self.current.value!r} at position {self.current.pos}"
            )
        return value

    def _parse_value(self) -> Any:
        tok = self.current
        if tok is None:
            raise JSONError("Unexpected end of input while parsing value")

        if tok.type == "LBRACE":
            return self._parse_object()
        elif tok.type == "LBRACKET":
            return self._parse_array()
        elif tok.type == "STRING":
            return self._parse_string()
        elif tok.type == "NUMBER":
            return self._parse_number()
        elif tok.type == "TRUE":
            self.pos += 1
            return True
        elif tok.type == "FALSE":
            self.pos += 1
            return False
        elif tok.type == "NULL":
            self.pos += 1
            return None
        else:
            raise JSONError(
                f"Unexpected token {tok.value!r} ({tok.type}) at position {tok.pos} — "
                f"not a valid JSON value"
            )

    def _parse_string(self) -> str:
        tok = self._expect("STRING")
        # Strip surrounding quotes and unescape
        inner = tok.value[1:-1]
        return _unescape(inner, tok.pos + 1)

    def _parse_number(self) -> int | float:
        tok = self._expect("NUMBER")
        raw = tok.value
        # Use Python's built-in numeric parsing — this is still from scratch
        # because we did the lexical analysis ourselves.
        if 'e' in raw or 'E' in raw or '.' in raw:
            return float(raw)
        return int(raw)

    def _parse_array(self) -> list[Any]:
        self._expect("LBRACKET")
        arr: list[Any] = []
        # Empty array?
        if self.current and self.current.type == "RBRACKET":
            self._expect("RBRACKET")
            return arr

        while True:
            arr.append(self._parse_value())
            tok = self._expect("COMMA", "RBRACKET")
            if tok.type == "RBRACKET":
                break
            # If we saw COMMA, check for trailing comma before next value
            if self.current and self.current.type == "RBRACKET":
                raise JSONError(
                    f"Trailing comma in array at position {self.current.pos}"
                )
        return arr

    def _parse_object(self) -> dict[str, Any]:
        self._expect("LBRACE")
        obj: dict[str, Any] = {}
        # Empty object?
        if self.current and self.current.type == "RBRACE":
            self._expect("RBRACE")
            return obj

        while True:
            # Key must be a string
            key_tok = self.current
            if key_tok is None:
                raise JSONError("Unexpected end of input while parsing object key")
            if key_tok.type != "STRING":
                raise JSONError(
                    f"Object key must be a string, got {key_tok.value!r} ({key_tok.type}) "
                    f"at position {key_tok.pos}"
                )
            key = self._parse_string()
            self._expect("COLON")
            obj[key] = self._parse_value()
            tok = self._expect("COMMA", "RBRACE")
            if tok.type == "RBRACE":
                break
            # Trailing comma check
            if self.current and self.current.type == "RBRACE":
                raise JSONError(
                    f"Trailing comma in object at position {self.current.pos}"
                )
        return obj


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def parse_json(text: str) -> Any:
    """Parse a JSON string and return the corresponding Python object."""
    tokenizer = Tokenizer(text)
    parser = Parser(tokenizer.tokens, text)
    return parser.parse()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def run_tests() -> None:
    tests_passed = 0
    tests_failed = 0

    def check(name: str, got: Any, expected: Any) -> None:
        nonlocal tests_passed, tests_failed
        if got == expected:
            print(f"  [PASS] {name}")
            tests_passed += 1
        else:
            print(f"  [FAIL] {name}")
            print(f"         Expected: {expected!r}")
            print(f"         Got:      {got!r}")
            tests_failed += 1

    def check_error(name: str, text: str, expected_msg: str) -> None:
        nonlocal tests_passed, tests_failed
        try:
            parse_json(text)
            print(f"  [FAIL] {name} — expected exception but got none")
            tests_failed += 1
        except JSONError as e:
            msg = str(e)
            if expected_msg in msg.lower():
                print(f"  [PASS] {name}")
                tests_passed += 1
            else:
                print(f"  [FAIL] {name}")
                print(f"         Expected message containing: {expected_msg!r}")
                print(f"         Got: {msg!r}")
                tests_failed += 1
        except Exception as e:
            print(f"  [FAIL] {name} — wrong exception type: {type(e).__name__}: {e}")
            tests_failed += 1

    print("\n=== JSON Parser Tests ===\n")

    # 1. Integer
    check("integer", parse_json("42"), 42)

    # 2. Negative float
    check("negative float", parse_json("-3.14"), -3.14)

    # 3. true
    check("true", parse_json("true"), True)

    # 4. false
    check("false", parse_json("false"), False)

    # 5. null
    check("null", parse_json("null"), None)

    # 6. Simple string
    check("simple string", parse_json('"hello"'), "hello")

    # 7. Array of numbers
    check("array of ints", parse_json("[1, 2, 3]"), [1, 2, 3])

    # 8. Empty array
    check("empty array", parse_json("[]"), [])

    # 9. Simple object
    check("simple object", parse_json('{"a": 1, "b": 2}'), {"a": 1, "b": 2})

    # 10. Empty object
    check("empty object", parse_json("{}"), {})

    # 11. Nested structures
    check(
        "nested object/array",
        parse_json('{"x": [1, {"y": 2}]}'),
        {"x": [1, {"y": 2}]},
    )

    # 12. Array of objects
    check(
        "array of objects",
        parse_json('[{"a": 1}, {"b": 2}]'),
        [{"a": 1}, {"b": 2}],
    )

    # 13. Escaped newline
    check("escaped newline", parse_json('"hello\\nworld"'), "hello\nworld")

    # 14. Escaped quotes
    check(
        "escaped quotes",
        parse_json('"quote: \\\"hi\\\""'),
        'quote: "hi"',
    )

    # 15. Error: unclosed object
    check_error(
        "unclosed object",
        '{"a": 1',
        "unexpected end",
    )

    # 16. Error: missing colon
    check_error(
        "missing colon",
        '{"a" 1}',
        "colon",
    )

    # 17. Error: trailing comma in object
    check_error(
        "trailing comma",
        '{"a": 1,}',
        "trailing comma",
    )

    # -- Bonus escape tests --
    check("escaped backslash", parse_json('"a\\\\b"'), "a\\b")
    check("escaped slash", parse_json('"a\\/b"'), "a/b")
    check("escaped tab", parse_json('"a\\tb"'), "a\tb")
    check("escaped carriage return", parse_json('"a\\rb"'), "a\rb")
    check("escaped backspace", parse_json('"a\\bb"'), "a\bb")
    check("escaped formfeed", parse_json('"a\\fb"'), "a\fb")

    # Unicode escape
    check("unicode escape", parse_json('"\\u0048\\u0065\\u006c\\u006c\\u006f"'), "Hello")
    check("unicode smiley", parse_json('"\\u263A"'), "\u263A")

    # Nested arrays
    check("nested arrays", parse_json("[[1,2],[3,4]]"), [[1, 2], [3, 4]])

    # Whitespace tolerance
    check(
        "whitespace tolerance",
        parse_json('  {  "a"  :  [ 1 , 2 ]  }  '),
        {"a": [1, 2]},
    )

    # Scientific notation
    check("scientific notation", parse_json("1.23e2"), 123.0)
    check("negative exponent", parse_json("1e-3"), 0.001)

    print("\n" + "=" * 40)
    print(f"Results: {tests_passed} passed, {tests_failed} failed")
    print("=" * 40 + "\n")

    if tests_failed > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    run_tests()
