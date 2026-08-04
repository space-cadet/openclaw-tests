#!/usr/bin/env python3
"""
T2-flash-json_parser.py
A JSON parser built from scratch in Python.
No json module or ast.literal_eval — tokenizer and parser are hand-written.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Optional


class TokenType(Enum):
    # Structural
    LBRACE = auto()      # {
    RBRACE = auto()      # }
    LBRACKET = auto()    # [
    RBRACKET = auto()    # ]
    COLON = auto()       # :
    COMMA = auto()       # ,
    # Literals
    STRING = auto()
    NUMBER = auto()
    TRUE = auto()
    FALSE = auto()
    NULL = auto()
    EOF = auto()


@dataclass(frozen=True)
class Token:
    type: TokenType
    value: Any
    pos: int  # index in source string where token begins


class JSONError(Exception):
    """Raised when input is not valid JSON."""


class Tokenizer:
    """Break raw JSON text into a flat list of tokens."""

    KEYWORD_MAP = {
        "true": TokenType.TRUE,
        "false": TokenType.FALSE,
        "null": TokenType.NULL,
    }

    def __init__(self, text: str) -> None:
        self.text = text
        self.n = len(text)
        self.pos = 0
        self.tokens: list[Token] = []

    def error(self, msg: str) -> None:
        # Show a snippet around the current position
        snippet = self.text[max(0, self.pos - 15):self.pos + 15]
        raise JSONError(f"{msg} at position {self.pos} (near: ...{snippet!r}...)")

    def peek(self) -> Optional[str]:
        return self.text[self.pos] if self.pos < self.n else None

    def advance(self) -> str:
        ch = self.text[self.pos]
        self.pos += 1
        return ch

    def skip_whitespace(self) -> None:
        while self.pos < self.n and self.text[self.pos] in " \t\r\n":
            self.pos += 1

    def read_string(self) -> str:
        """Consume a double-quoted string; assumes opening '"' already consumed."""
        start = self.pos - 1  # include opening quote for error messages
        result = []
        while True:
            if self.pos >= self.n:
                raise JSONError(f"Unterminated string starting at position {start}")
            ch = self.advance()
            if ch == '"':
                return "".join(result)
            if ch == "\\":
                if self.pos >= self.n:
                    raise JSONError(f"Unterminated escape sequence in string at position {start}")
                esc = self.advance()
                if esc == '"':
                    result.append('"')
                elif esc == "\\":
                    result.append("\\")
                elif esc == "/":
                    result.append("/")
                elif esc == "b":
                    result.append("\b")
                elif esc == "f":
                    result.append("\f")
                elif esc == "n":
                    result.append("\n")
                elif esc == "r":
                    result.append("\r")
                elif esc == "t":
                    result.append("\t")
                elif esc == "u":
                    # Expect exactly 4 hex digits
                    if self.pos + 4 > self.n:
                        raise JSONError(f"Incomplete unicode escape at position {self.pos}")
                    hex_digits = self.text[self.pos:self.pos + 4]
                    if not all(c in "0123456789abcdefABCDEF" for c in hex_digits):
                        raise JSONError(f"Invalid unicode escape \\u{hex_digits} at position {self.pos}")
                    code_point = int(hex_digits, 16)
                    result.append(chr(code_point))
                    self.pos += 4
                else:
                    raise JSONError(f"Invalid escape character '\\{esc}' at position {self.pos - 1}")
            elif ch == "\n" or ch == "\r":
                raise JSONError(f"Unescaped line break in string at position {self.pos - 1}")
            else:
                # Control characters (U+0000–U+001F) must be escaped per JSON spec
                if ord(ch) < 0x20:
                    raise JSONError(f"Unescaped control character at position {self.pos - 1}")
                result.append(ch)

    NUMBER_RE = re.compile(r"-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?")

    def read_number(self) -> float | int:
        """Consume a number literal; assumes current char is part of it."""
        match = self.NUMBER_RE.match(self.text, self.pos - 1)
        if not match:
            # Shouldn't happen given how we call it, but be safe
            raise JSONError(f"Invalid number at position {self.pos - 1}")
        raw = match.group(0)
        self.pos += len(raw) - 1
        # Preserve exact int vs float semantics of JSON
        if "." in raw or "e" in raw or "E" in raw:
            return float(raw)
        return int(raw)

    def tokenize(self) -> list[Token]:
        while True:
            self.skip_whitespace()
            if self.pos >= self.n:
                self.tokens.append(Token(TokenType.EOF, None, self.pos))
                break
            start = self.pos
            ch = self.advance()

            if ch == '{':
                self.tokens.append(Token(TokenType.LBRACE, ch, start))
            elif ch == '}':
                self.tokens.append(Token(TokenType.RBRACE, ch, start))
            elif ch == '[':
                self.tokens.append(Token(TokenType.LBRACKET, ch, start))
            elif ch == ']':
                self.tokens.append(Token(TokenType.RBRACKET, ch, start))
            elif ch == ':':
                self.tokens.append(Token(TokenType.COLON, ch, start))
            elif ch == ',':
                self.tokens.append(Token(TokenType.COMMA, ch, start))
            elif ch == '"':
                s = self.read_string()
                self.tokens.append(Token(TokenType.STRING, s, start))
            elif ch == '-' or ch.isdigit():
                num = self.read_number()
                self.tokens.append(Token(TokenType.NUMBER, num, start))
            elif ch.isalpha():
                # keywords: true, false, null
                while self.pos < self.n and self.text[self.pos].isalpha():
                    ch += self.advance()
                tt = self.KEYWORD_MAP.get(ch)
                if tt is None:
                    self.error(f"Unexpected keyword {ch!r}")
                self.tokens.append(Token(tt, ch, start))
            else:
                self.error(f"Unexpected character {ch!r}")

        return self.tokens


class Parser:
    """Transform a token list into Python objects."""

    def __init__(self, tokens: list[Token], source: str) -> None:
        self.tokens = tokens
        self.source = source
        self.pos = 0

    def current(self) -> Token:
        return self.tokens[self.pos]

    def error(self, msg: str) -> None:
        tok = self.current()
        raise JSONError(f"{msg} at position {tok.pos} (token={tok.type.name}, value={tok.value!r})")

    def consume(self, expected: TokenType) -> Token:
        tok = self.current()
        if tok.type != expected:
            self.error(f"Expected {expected.name} but found {tok.type.name}")
        self.pos += 1
        return tok

    def parse(self) -> Any:
        value = self.parse_value()
        if self.current().type != TokenType.EOF:
            self.error("Unexpected trailing data after valid JSON value")
        return value

    def parse_value(self) -> Any:
        tok = self.current()
        if tok.type == TokenType.LBRACE:
            return self.parse_object()
        elif tok.type == TokenType.LBRACKET:
            return self.parse_array()
        elif tok.type == TokenType.STRING:
            self.pos += 1
            return tok.value
        elif tok.type == TokenType.NUMBER:
            self.pos += 1
            return tok.value
        elif tok.type == TokenType.TRUE:
            self.pos += 1
            return True
        elif tok.type == TokenType.FALSE:
            self.pos += 1
            return False
        elif tok.type == TokenType.NULL:
            self.pos += 1
            return None
        else:
            self.error(f"Unexpected token {tok.type.name}")

    def parse_object(self) -> dict:
        self.consume(TokenType.LBRACE)
        obj: dict[str, Any] = {}
        # Empty object?
        if self.current().type == TokenType.RBRACE:
            self.pos += 1
            return obj
        while True:
            key_tok = self.current()
            if key_tok.type != TokenType.STRING:
                self.error(f"Object key must be a string, found {key_tok.type.name}")
            key = key_tok.value
            self.pos += 1
            self.consume(TokenType.COLON)
            value = self.parse_value()
            if key in obj:
                # JSON technically allows duplicate keys, but for simplicity we overwrite.
                # We'll keep the last value to match Python json behavior.
                pass
            obj[key] = value
            tok = self.current()
            if tok.type == TokenType.COMMA:
                self.pos += 1
                # Check for trailing comma before the closing brace
                if self.current().type == TokenType.RBRACE:
                    self.error("Trailing comma in object")
                continue
            elif tok.type == TokenType.EOF:
                self.error("Unterminated object: expected ',' or '}'")
            elif tok.type == TokenType.RBRACE:
                self.pos += 1
                break
            else:
                self.error(f"Expected ',' or '}}' in object, found {tok.type.name}")
        return obj

    def parse_array(self) -> list:
        self.consume(TokenType.LBRACKET)
        arr: list[Any] = []
        # Empty array?
        if self.current().type == TokenType.RBRACKET:
            self.pos += 1
            return arr
        while True:
            value = self.parse_value()
            arr.append(value)
            tok = self.current()
            if tok.type == TokenType.COMMA:
                self.pos += 1
                # Check for trailing comma before closing bracket
                if self.current().type == TokenType.RBRACKET:
                    self.error("Trailing comma in array")
                continue
            elif tok.type == TokenType.EOF:
                self.error("Unterminated array: expected ',' or ']'")
            elif tok.type == TokenType.RBRACKET:
                self.pos += 1
                break
            else:
                self.error(f"Expected ',' or ']' in array, found {tok.type.name}")
        return arr


def parse_json(text: str) -> Any:
    """Parse a JSON string and return the corresponding Python object."""
    tokenizer = Tokenizer(text)
    tokens = tokenizer.tokenize()
    parser = Parser(tokens, text)
    return parser.parse()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def run_tests():
    tests = [
        # (input_json, expected_value_or_exception_substring)
        ('42', 42),
        ('-3.14', -3.14),
        ('true', True),
        ('false', False),
        ('null', None),
        ('"hello"', "hello"),
        ('[1, 2, 3]', [1, 2, 3]),
        ('[]', []),
        ('{"a": 1, "b": 2}', {"a": 1, "b": 2}),
        ('{}', {}),
        ('{"x": [1, {"y": 2}]}', {"x": [1, {"y": 2}]}),
        ('[{"a": 1}, {"b": 2}]', [{"a": 1}, {"b": 2}]),
        ('"hello\\nworld"', "hello\nworld"),
        ('"quote: \\\"hi\\\""', 'quote: "hi"'),
        # Error cases
        ('{"a": 1', "Unterminated"),          # unclosed object
        ('{"a" 1}', "Expected COLON"),        # missing colon
        ('[1, 2,]', "Trailing comma"),        # trailing comma in array
        ('{"a": 1,}', "Trailing comma"),      # trailing comma in object
    ]

    passed = 0
    failed = 0

    for i, (inp, expected) in enumerate(tests, 1):
        label = f"Test {i:2d}: {inp!r}"
        try:
            result = parse_json(inp)
        except JSONError as e:
            result = str(e)

        if isinstance(expected, type) and issubclass(expected, Exception):
            # Expecting an exception type — we got some exception string
            passed += 1
            print(f"✅ {label} -> raised as expected")
        elif isinstance(expected, str) and ("error" in expected.lower() or expected in str(result)):
            # Expecting a specific error message substring
            if expected in str(result):
                passed += 1
                print(f"✅ {label} -> error contains {expected!r}")
            else:
                failed += 1
                print(f"❌ {label} -> expected error containing {expected!r}, got {result!r}")
        else:
            # Normal value comparison
            if result == expected:
                passed += 1
                print(f"✅ {label} -> {result!r}")
            else:
                failed += 1
                print(f"❌ {label} -> expected {expected!r}, got {result!r}")

    print()
    total = passed + failed
    print(f"Summary: {passed}/{total} passed, {failed}/{total} failed")
    if failed == 0:
        print("All tests passed! 🎉")
    return failed == 0


if __name__ == "__main__":
    run_tests()
