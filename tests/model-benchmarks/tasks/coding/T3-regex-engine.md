# Task T3: Regular Expression Engine

## Difficulty: Medium

Build a simple regex engine in Python supporting basic patterns.

### Requirements
1. Match literal characters: `a`, `b`, `1`
2. Metacharacters:
   - `.` — matches any single character
   - `*` — zero or more of preceding element
   - `+` — one or more of preceding element
   - `?` — zero or one of preceding element
   - `^` — start of string anchor
   - `$` — end of string anchor
3. Character classes: `[abc]`, `[a-z]`, `[^abc]` (negation)
4. Groups: `(abc)` — capture groups
5. Alternation: `a|b` — match either a or b
6. No `re` module

### Test Cases (must all pass)

```python
# Literals
match("abc", "abc") => True
match("abc", "abd") => False

# Dot
match("a.c", "abc") => True
match("a.c", "ac") => False

# Star
match("ab*c", "ac") => True
match("ab*c", "abc") => True
match("ab*c", "abbc") => True
match("ab*c", "abx") => False

# Plus
match("ab+c", "ac") => False
match("ab+c", "abc") => True
match("ab+c", "abbc") => True

# Question
match("ab?c", "ac") => True
match("ab?c", "abc") => True
match("ab?c", "abbc") => False

# Anchors
match("^abc", "abc") => True
match("^abc", "xabc") => False
match("abc$", "abc") => True
match("abc$", "abcx") => False

# Character class
match("[aeiou]", "a") => True
match("[aeiou]", "x") => False
match("[^aeiou]", "x") => True
match("[a-z]", "m") => True
match("[a-z]", "M") => False

# Alternation
match("cat|dog", "cat") => True
match("cat|dog", "dog") => True
match("cat|dog", "bird") => False

# Groups
match("(ab)+", "abab") => True
match("(ab)+", "ababa") => False

# Complex
match("a(b|c)*d", "ad") => True
match("a(b|c)*d", "abcd") => True
match("a(b|c)*d", "abbd") => False
```

### Output Format
Write `regex_engine.py` with `match(pattern, text)` and `run_tests()`.

### Scoring
- Correctness: all tests pass
- Efficiency: avoid catastrophic backtracking where possible
- Code quality: clean NFA/DFA or recursive implementation
