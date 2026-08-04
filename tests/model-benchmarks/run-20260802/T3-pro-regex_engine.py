#!/usr/bin/env python3
"""
Regular Expression Engine from Scratch

Supports:
  - Literal characters: a, b, 1
  - . (any character)
  - * (zero or more)
  - + (one or more)
  - ? (zero or one)
  - ^ (start anchor)
  - $ (end anchor)
  - [abc] character classes, [a-z] ranges, [^abc] negation
  - (abc) groups
  - a|b alternation

No `re` module used.
"""


# ---------------------------------------------------------------------------
# AST Nodes
# ---------------------------------------------------------------------------

class Literal:
    __slots__ = ("char",)
    def __init__(self, char):
        self.char = char


class Any:
    pass


class Sequence:
    __slots__ = ("nodes",)
    def __init__(self, nodes):
        self.nodes = nodes


class Group:
    __slots__ = ("node",)
    def __init__(self, node):
        self.node = node


class Alternation:
    __slots__ = ("left", "right")
    def __init__(self, left, right):
        self.left = left
        self.right = right


class Star:
    __slots__ = ("node",)
    def __init__(self, node):
        self.node = node


class Plus:
    __slots__ = ("node",)
    def __init__(self, node):
        self.node = node


class Question:
    __slots__ = ("node",)
    def __init__(self, node):
        self.node = node


class CharClass:
    __slots__ = ("chars", "negated")
    def __init__(self, chars, negated=False):
        self.chars = chars
        self.negated = negated


class StartAnchor:
    pass


class EndAnchor:
    pass


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class Parser:
    def __init__(self, pattern):
        self.pattern = pattern
        self.pos = 0
        self.n = len(pattern)

    def parse(self):
        node = self.parse_alternation()
        if self.pos != self.n:
            raise ValueError(
                f"Unexpected character at position {self.pos}: "
                f"{self.pattern[self.pos]!r}"
            )
        return node

    def parse_alternation(self):
        left = self.parse_sequence()
        if self.peek() == "|":
            self.consume("|")
            right = self.parse_alternation()
            return Alternation(left, right)
        return left

    def parse_sequence(self):
        nodes = []
        while self.pos < self.n and self.peek() not in ")|":
            nodes.append(self.parse_factor())
        if len(nodes) == 0:
            return Sequence([])
        if len(nodes) == 1:
            return nodes[0]
        return Sequence(nodes)

    def parse_factor(self):
        node = self.parse_primary()
        if self.peek() == "*":
            self.consume("*")
            return Star(node)
        elif self.peek() == "+":
            self.consume("+")
            return Plus(node)
        elif self.peek() == "?":
            self.consume("?")
            return Question(node)
        return node

    def parse_primary(self):
        ch = self.peek()
        if ch == "^":
            self.consume("^")
            return StartAnchor()
        elif ch == "$":
            self.consume("$")
            return EndAnchor()
        elif ch == ".":
            self.consume(".")
            return Any()
        elif ch == "(":
            self.consume("(")
            node = self.parse_alternation()
            self.consume(")")
            return Group(node)
        elif ch == "[":
            return self.parse_charclass()
        elif ch is None:
            raise ValueError("Unexpected end of pattern")
        else:
            self.consume(ch)
            return Literal(ch)

    def parse_charclass(self):
        self.consume("[")
        negated = False
        if self.peek() == "^":
            self.consume("^")
            negated = True
        chars = set()
        while self.peek() != "]":
            if self.peek() is None:
                raise ValueError("Unclosed character class")
            start = self.peek()
            self.consume(start)
            # Range like a-z
            if (
                self.peek() == "-"
                and self.pos + 1 < self.n
                and self.pattern[self.pos + 1] != "]"
            ):
                self.consume("-")
                end = self.peek()
                if end is None:
                    raise ValueError("Unclosed character class")
                self.consume(end)
                for c in range(ord(start), ord(end) + 1):
                    chars.add(chr(c))
            else:
                chars.add(start)
        self.consume("]")
        return CharClass(chars, negated)

    def peek(self):
        if self.pos < self.n:
            return self.pattern[self.pos]
        return None

    def consume(self, expected):
        if self.pos >= self.n or self.pattern[self.pos] != expected:
            raise ValueError(
                f"Expected {expected!r} at position {self.pos}, "
                f"got {self.peek()!r}"
            )
        self.pos += 1


# ---------------------------------------------------------------------------
# Matcher
# ---------------------------------------------------------------------------

def match_node(node, text, pos):
    """
    Try to match `node` starting at `pos` in `text`.
    Returns a list of possible end positions (may be empty).
    """
    if isinstance(node, Literal):
        if pos < len(text) and text[pos] == node.char:
            return [pos + 1]
        return []

    elif isinstance(node, Any):
        if pos < len(text):
            return [pos + 1]
        return []

    elif isinstance(node, StartAnchor):
        if pos == 0:
            return [pos]
        return []

    elif isinstance(node, EndAnchor):
        if pos == len(text):
            return [pos]
        return []

    elif isinstance(node, CharClass):
        if pos < len(text):
            in_class = text[pos] in node.chars
            if (in_class and not node.negated) or (not in_class and node.negated):
                return [pos + 1]
        return []

    elif isinstance(node, Sequence):
        positions = [pos]
        for child in node.nodes:
            new_positions = []
            for p in positions:
                new_positions.extend(match_node(child, text, p))
            # Deduplicate while preserving order
            seen = set()
            deduped = []
            for p in new_positions:
                if p not in seen:
                    seen.add(p)
                    deduped.append(p)
            positions = deduped
            if not positions:
                return []
        return positions

    elif isinstance(node, Group):
        return match_node(node.node, text, pos)

    elif isinstance(node, Alternation):
        left = match_node(node.left, text, pos)
        right = match_node(node.right, text, pos)
        # Merge and deduplicate
        seen = set()
        result = []
        for p in left + right:
            if p not in seen:
                seen.add(p)
                result.append(p)
        return result

    elif isinstance(node, Star):
        positions = [pos]
        changed = True
        while changed:
            changed = False
            new_positions = []
            for p in positions:
                for r in match_node(node.node, text, p):
                    if r not in positions and r not in new_positions:
                        if r == p:
                            # Zero-width match — skip to avoid infinite loop
                            continue
                        new_positions.append(r)
                        changed = True
            positions.extend(new_positions)
        return positions

    elif isinstance(node, Plus):
        # Must match at least once
        first = match_node(node.node, text, pos)
        if not first:
            return []
        positions = first
        changed = True
        while changed:
            changed = False
            new_positions = []
            for p in positions:
                for r in match_node(node.node, text, p):
                    if r not in positions and r not in new_positions:
                        if r == p:
                            continue
                        new_positions.append(r)
                        changed = True
            positions.extend(new_positions)
        return positions

    elif isinstance(node, Question):
        results = [pos]
        results.extend(match_node(node.node, text, pos))
        seen = set()
        deduped = []
        for r in results:
            if r not in seen:
                seen.add(r)
                deduped.append(r)
        return deduped

    else:
        raise ValueError(f"Unknown node type: {type(node).__name__}")


def match(pattern, text):
    """
    Return True if `pattern` matches anywhere in `text`.
    ^ forces match at start; $ forces match at end.
    """
    if not pattern:
        return True  # empty pattern matches everywhere

    parser = Parser(pattern)
    ast = parser.parse()

    # Try every possible starting position in text
    for start in range(len(text) + 1):
        results = match_node(ast, text, start)
        if results:
            return True

    return False


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def run_tests():
    tests = [
        # (pattern, text, expected)
        ("abc", "abc", True),
        ("abc", "abd", False),
        ("a.c", "abc", True),
        ("ab*c", "ac", True),
        ("ab*c", "abc", True),
        ("ab*c", "abbc", True),
        ("ab+c", "ac", False),
        ("ab+c", "abc", True),
        ("ab?c", "ac", True),
        ("ab?c", "abbc", False),
        ("^abc", "abc", True),
        ("^abc", "xabc", False),
        ("[aeiou]", "a", True),
        ("[^aeiou]", "x", True),
        ("cat|dog", "cat", True),
        ("cat|dog", "bird", False),
        ("(ab)+", "abab", True),
        ("a(b|c)*d", "ad", True),
        ("a(b|c)*d", "abcd", True),
    ]

    passed = 0
    failed = 0

    for pattern, text, expected in tests:
        try:
            result = match(pattern, text)
            status = "PASS" if result == expected else "FAIL"
            if status == "PASS":
                passed += 1
            else:
                failed += 1
            print(f"[{status}] match({pattern!r}, {text!r}) = {result} (expected {expected})")
        except Exception as e:
            failed += 1
            print(
                f"[FAIL] match({pattern!r}, {text!r}) raised "
                f"{type(e).__name__}: {e}"
            )

    print(f"\n{'=' * 40}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
    print(f"{'=' * 40}")

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
