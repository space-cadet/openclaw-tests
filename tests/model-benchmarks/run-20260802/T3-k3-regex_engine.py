#!/usr/bin/env python3
"""
Regex engine from scratch.
Supports: literals, ., *, +, ?, ^, $, [abc], [a-z], [^abc], (groups), a|b
"""

# ---------------------------------------------------------------------------
# AST Nodes
# ---------------------------------------------------------------------------

class ASTNode:
    pass


class Literal(ASTNode):
    def __init__(self, char):
        self.char = char


class Dot(ASTNode):
    pass


class CharClass(ASTNode):
    def __init__(self, chars, negated=False):
        self.chars = chars
        self.negated = negated


class Group(ASTNode):
    def __init__(self, node):
        self.node = node


class Sequence(ASTNode):
    def __init__(self, nodes):
        self.nodes = nodes


class Alternation(ASTNode):
    def __init__(self, left, right):
        self.left = left
        self.right = right


class Star(ASTNode):
    def __init__(self, node):
        self.node = node


class Plus(ASTNode):
    def __init__(self, node):
        self.node = node


class Question(ASTNode):
    def __init__(self, node):
        self.node = node


class AnchorStart(ASTNode):
    pass


class AnchorEnd(ASTNode):
    pass


# ---------------------------------------------------------------------------
# Parser (recursive descent)
# ---------------------------------------------------------------------------

class Parser:
    def __init__(self, pattern):
        self.pattern = pattern
        self.pos = 0
        self.n = len(pattern)

    def peek(self):
        if self.pos < self.n:
            return self.pattern[self.pos]
        return None

    def consume(self):
        c = self.peek()
        self.pos += 1
        return c

    def parse(self):
        if self.peek() is None:
            return Sequence([])
        return self.parse_alternation()

    def parse_alternation(self):
        left = self.parse_sequence()
        if self.peek() == '|':
            self.consume()
            right = self.parse_alternation()
            return Alternation(left, right)
        return left

    def parse_sequence(self):
        nodes = []
        while self.peek() is not None and self.peek() not in '|)':
            nodes.append(self.parse_quantified())
        if len(nodes) == 0:
            return Sequence([])
        if len(nodes) == 1:
            return nodes[0]
        return Sequence(nodes)

    def parse_quantified(self):
        node = self.parse_atom()
        c = self.peek()
        if c == '*':
            self.consume()
            return Star(node)
        elif c == '+':
            self.consume()
            return Plus(node)
        elif c == '?':
            self.consume()
            return Question(node)
        return node

    def parse_atom(self):
        c = self.consume()
        if c is None:
            raise ValueError("Unexpected end of pattern")
        if c == '.':
            return Dot()
        elif c == '^':
            return AnchorStart()
        elif c == '$':
            return AnchorEnd()
        elif c == '(':
            node = self.parse_alternation()
            if self.peek() != ')':
                raise ValueError("Expected ')'")
            self.consume()
            return Group(node)
        elif c == '[':
            return self.parse_charclass()
        else:
            return Literal(c)

    def parse_charclass(self):
        negated = False
        if self.peek() == '^':
            self.consume()
            negated = True
        chars = set()
        while self.peek() is not None and self.peek() != ']':
            c = self.consume()
            if c is None:
                raise ValueError("Unterminated character class")
            # Range like a-z
            if (self.peek() == '-' and self.pos + 1 < self.n
                    and self.pattern[self.pos + 1] != ']'):
                self.consume()  # '-'
                end = self.consume()
                if end is None:
                    raise ValueError("Unterminated character class")
                for ch in range(ord(c), ord(end) + 1):
                    chars.add(chr(ch))
            else:
                chars.add(c)
        if self.peek() != ']':
            raise ValueError("Expected ']'")
        self.consume()
        return CharClass(chars, negated)


# ---------------------------------------------------------------------------
# Matcher (backtracking, returns possible end positions)
# ---------------------------------------------------------------------------

def match_node(node, text, pos):
    """Return a list of positions reachable after matching *node* starting at *pos*."""
    if isinstance(node, Literal):
        if pos < len(text) and text[pos] == node.char:
            return [pos + 1]
        return []

    elif isinstance(node, Dot):
        if pos < len(text):
            return [pos + 1]
        return []

    elif isinstance(node, CharClass):
        if pos < len(text):
            c = text[pos]
            in_class = c in node.chars
            if (in_class and not node.negated) or (not in_class and node.negated):
                return [pos + 1]
        return []

    elif isinstance(node, Sequence):
        if not node.nodes:
            return [pos]
        positions = [pos]
        for child in node.nodes:
            new_positions = []
            for p in positions:
                new_positions.extend(match_node(child, text, p))
            positions = new_positions
            if not positions:
                return []
        return positions

    elif isinstance(node, Alternation):
        left = match_node(node.left, text, pos)
        right = match_node(node.right, text, pos)
        return left + right

    elif isinstance(node, Star):
        positions = {pos}
        result = {pos}
        while True:
            new_positions = set()
            for p in positions:
                for np in match_node(node.node, text, p):
                    if np not in result:
                        new_positions.add(np)
                        result.add(np)
            if not new_positions:
                break
            positions = new_positions
        return list(result)

    elif isinstance(node, Plus):
        first = match_node(node.node, text, pos)
        if not first:
            return []
        positions = set(first)
        result = set(first)
        while True:
            new_positions = set()
            for p in positions:
                for np in match_node(node.node, text, p):
                    if np not in result:
                        new_positions.add(np)
                        result.add(np)
            if not new_positions:
                break
            positions = new_positions
        return list(result)

    elif isinstance(node, Question):
        result = {pos}
        for np in match_node(node.node, text, pos):
            result.add(np)
        return list(result)

    elif isinstance(node, AnchorStart):
        if pos == 0:
            return [pos]
        return []

    elif isinstance(node, AnchorEnd):
        if pos == len(text):
            return [pos]
        return []

    elif isinstance(node, Group):
        return match_node(node.node, text, pos)

    else:
        raise ValueError(f"Unknown node type: {type(node)}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse(pattern):
    parser = Parser(pattern)
    return parser.parse()


def match(pattern, text):
    """Return True if *pattern* matches *text* (searching at any offset)."""
    ast = parse(pattern)
    for start in range(len(text) + 1):
        positions = match_node(ast, text, start)
        if len(text) in positions:
            return True
    return False


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def run_tests():
    tests = [
        # 1. literal match
        ("abc", "abc", True),
        ("abc", "abd", False),
        # 2. dot
        ("a.c", "abc", True),
        # 3. star
        ("ab*c", "ac", True),
        ("ab*c", "abc", True),
        ("ab*c", "abbc", True),
        # 4. plus
        ("ab+c", "ac", False),
        ("ab+c", "abc", True),
        # 5. question
        ("ab?c", "ac", True),
        ("ab?c", "abbc", False),
        # 6. anchors
        ("^abc", "abc", True),
        ("^abc", "xabc", False),
        # 7. character classes
        ("[aeiou]", "a", True),
        ("[^aeiou]", "x", True),
        # 8. alternation
        ("cat|dog", "cat", True),
        ("cat|dog", "bird", False),
        # 9. groups
        ("(ab)+", "abab", True),
        # 10. groups + star
        ("a(b|c)*d", "ad", True),
        ("a(b|c)*d", "abcd", True),
    ]

    passed = 0
    failed = 0

    for pattern, text, expected in tests:
        result = match(pattern, text)
        status = "PASS" if result == expected else "FAIL"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f"[{status}] match({pattern!r}, {text!r}) = {result} (expected {expected})")

    print(f"\nSummary: {passed}/{len(tests)} passed, {failed}/{len(tests)} failed")
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
