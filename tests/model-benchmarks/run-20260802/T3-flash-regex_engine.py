#!/usr/bin/env python3
"""
Regular Expression Engine from Scratch
Supports: literals, ., *, +, ?, ^, $, [classes], (groups), |
"""


class RegexEngine:
    """A regex engine implemented from scratch without the `re` module."""

    def __init__(self, pattern):
        self.pattern = pattern
        self.pos = 0
        self.tokens = self._tokenize()
        self.ast = self._parse()

    # ------------------------------------------------------------------
    # Tokenizer
    # ------------------------------------------------------------------
    def _tokenize(self):
        tokens = []
        i = 0
        while i < len(self.pattern):
            ch = self.pattern[i]
            if ch == '.':
                tokens.append(('ANY', ch))
            elif ch == '*':
                tokens.append(('STAR', ch))
            elif ch == '+':
                tokens.append(('PLUS', ch))
            elif ch == '?':
                tokens.append(('QUESTION', ch))
            elif ch == '^':
                tokens.append(('CARET', ch))
            elif ch == '$':
                tokens.append(('DOLLAR', ch))
            elif ch == '(':
                tokens.append(('LPAREN', ch))
            elif ch == ')':
                tokens.append(('RPAREN', ch))
            elif ch == '|':
                tokens.append(('PIPE', ch))
            elif ch == '[':
                # Parse character class
                i += 1
                negated = False
                if i < len(self.pattern) and self.pattern[i] == '^':
                    negated = True
                    i += 1
                chars = set()
                while i < len(self.pattern) and self.pattern[i] != ']':
                    if i + 2 < len(self.pattern) and self.pattern[i + 1] == '-' and self.pattern[i + 2] != ']':
                        start = self.pattern[i]
                        end = self.pattern[i + 2]
                        for c in range(ord(start), ord(end) + 1):
                            chars.add(chr(c))
                        i += 3
                    else:
                        chars.add(self.pattern[i])
                        i += 1
                # Skip the closing ]
                if i < len(self.pattern) and self.pattern[i] == ']':
                    i += 1
                tokens.append(('CLASS', chars, negated))
                continue
            else:
                tokens.append(('LITERAL', ch))
            i += 1
        tokens.append(('EOF', None))
        return tokens

    # ------------------------------------------------------------------
    # Parser -> AST
    # ------------------------------------------------------------------
    def _parse(self):
        self.tok_pos = 0
        node = self._parse_expr()
        return node

    def _current(self):
        return self.tokens[self.tok_pos]

    def _advance(self):
        tok = self._current()
        self.tok_pos += 1
        return tok

    def _parse_expr(self):
        """expr := term ( '|' term )*"""
        left = self._parse_term()
        while self._current()[0] == 'PIPE':
            self._advance()
            right = self._parse_term()
            left = ('ALT', left, right)
        return left

    def _parse_term(self):
        """term := factor+"""
        factors = []
        while self._current()[0] in ('LITERAL', 'ANY', 'CLASS', 'LPAREN', 'CARET', 'DOLLAR'):
            factors.append(self._parse_factor())
        if len(factors) == 1:
            return factors[0]
        return ('SEQ', factors)

    def _parse_factor(self):
        """factor := atom [ '*', '+', '?' ]"""
        atom = self._parse_atom()
        while self._current()[0] in ('STAR', 'PLUS', 'QUESTION'):
            op = self._advance()[0]
            if op == 'STAR':
                atom = ('QUANT', atom, 0, None)
            elif op == 'PLUS':
                atom = ('QUANT', atom, 1, None)
            elif op == 'QUESTION':
                atom = ('QUANT', atom, 0, 1)
        return atom

    def _parse_atom(self):
        tok = self._current()
        typ = tok[0]

        if typ == 'LITERAL':
            self._advance()
            return ('LIT', tok[1])
        elif typ == 'ANY':
            self._advance()
            return ('ANY',)
        elif typ == 'CLASS':
            self._advance()
            return ('CLASS', tok[1], tok[2])
        elif typ == 'CARET':
            self._advance()
            return ('ANCHOR', 'start')
        elif typ == 'DOLLAR':
            self._advance()
            return ('ANCHOR', 'end')
        elif typ == 'LPAREN':
            self._advance()
            node = self._parse_expr()
            if self._current()[0] != 'RPAREN':
                raise ValueError("Unmatched '(' in pattern")
            self._advance()
            return ('GROUP', node)
        else:
            # Empty expression
            return ('SEQ', [])

    # ------------------------------------------------------------------
    # Matcher (backtracking)
    # ------------------------------------------------------------------
    def match(self, text):
        """Try to match the pattern against the entire text."""
        results = self._match_at(self.ast, text, 0)
        # A match succeeds if any result reached the end of text
        # AND all anchors were satisfied.
        for pos in results:
            if pos == len(text):
                return True
        return False

    def _match_at(self, node, text, pos):
        """Return a set of possible positions after matching node."""
        typ = node[0]

        if typ == 'SEQ':
            results = {pos}
            for child in node[1]:
                new_results = set()
                for p in results:
                    new_results.update(self._match_at(child, text, p))
                results = new_results
                if not results:
                    break
            return results

        elif typ == 'LIT':
            if pos < len(text) and text[pos] == node[1]:
                return {pos + 1}
            return set()

        elif typ == 'ANY':
            if pos < len(text):
                return {pos + 1}
            return set()

        elif typ == 'CLASS':
            chars, negated = node[1], node[2]
            if pos < len(text):
                match = text[pos] in chars
                if negated:
                    match = not match
                if match:
                    return {pos + 1}
            return set()

        elif typ == 'ANCHOR':
            if node[1] == 'start':
                if pos == 0:
                    return {pos}
            elif node[1] == 'end':
                if pos == len(text):
                    return {pos}
            return set()

        elif typ == 'GROUP':
            return self._match_at(node[1], text, pos)

        elif typ == 'ALT':
            left = self._match_at(node[1], text, pos)
            right = self._match_at(node[2], text, pos)
            return left | right

        elif typ == 'QUANT':
            child, min_c, max_c = node[1], node[2], node[3]
            results = {pos}
            count = 0
            while True:
                if max_c is not None and count > max_c:
                    break
                if count >= min_c:
                    # All paths that have matched at least min_c times
                    pass
                # Try to match one more time
                new_results = set()
                for p in results:
                    new_results.update(self._match_at(child, text, p))
                # Remove positions we already had to avoid infinite loop
                new_results -= results
                if not new_results:
                    break
                results |= new_results
                count += len(new_results)  # approximate
            # Filter to only those that matched at least min_c times
            # Since we accumulate all paths, we need to check which ones
            # actually did min_c matches. Our accumulation does this naturally
            # because we only add to results when we match more.
            # But we need to ensure we return positions after at least min_c matches.
            # Actually, results contains all positions reachable after 0 or more matches.
            # We need to verify that each result in results has done at least min_c matches.
            # For simplicity, let's do a more direct approach:
            return self._match_quant(child, text, pos, min_c, max_c)

        return set()

    def _match_quant(self, child, text, pos, min_c, max_c):
        """Backtracking quantifier matching with proper max_c enforcement."""
        # State: (position, matches_so_far)
        results = {pos}

        # Minimum matches
        for _ in range(min_c):
            new_results = set()
            for p in results:
                new_results.update(self._match_at(child, text, p))
            results = new_results
            if not results:
                return set()

        all_results = set(results)
        if max_c is not None and min_c >= max_c:
            return all_results

        to_explore = [(p, min_c) for p in results]
        visited = {(p, min_c) for p in results}

        while to_explore:
            p, count = to_explore.pop()
            next_pos = self._match_at(child, text, p)
            for np in next_pos:
                new_count = count + 1
                if max_c is not None and new_count > max_c:
                    continue
                if (np, new_count) not in visited:
                    visited.add((np, new_count))
                    all_results.add(np)
                    to_explore.append((np, new_count))

        return all_results


def match(pattern, text):
    """Match a pattern against text (must match the entire text)."""
    engine = RegexEngine(pattern)
    return engine.match(text)


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------
def run_tests():
    tests = [
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
            if result == expected:
                passed += 1
            else:
                failed += 1
            print(f"  {status}: match({pattern!r}, {text!r}) => {result} (expected {expected})")
        except Exception as e:
            failed += 1
            print(f"  FAIL: match({pattern!r}, {text!r}) => EXCEPTION: {e}")

    print(f"\n{passed}/{len(tests)} passed, {failed}/{len(tests)} failed")
    return failed == 0


if __name__ == "__main__":
    import sys
    ok = run_tests()
    sys.exit(0 if ok else 1)
