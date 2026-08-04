# Task T2: JSON Parser from Scratch

## Difficulty: Easy-Medium

Build a JSON parser in Python that converts JSON strings into Python objects.

### Requirements
1. Parse: objects `{}`, arrays `[]`, strings `""`, numbers, booleans `true`/`false`, `null`
2. Handle nested structures (objects within arrays, arrays within objects)
3. Handle escaped characters in strings: `\"`, `\\`, `\/`, `\b`, `\f`, `\n`, `\r`, `\t`, `\uXXXX`
4. No `json` module or `ast.literal_eval` — build tokenizer and parser from scratch
5. Meaningful error messages for malformed JSON (line/column hints preferred)

### Test Cases (must all pass)

```python
# Primitives
parse_json("42") => 42
parse_json("-3.14") => -3.14
parse_json("true") => True
parse_json("false") => False
parse_json("null") => None
parse_json('"hello"') => "hello"

# Arrays
parse_json("[1, 2, 3]") => [1, 2, 3]
parse_json("[]") => []
parse_json('[true, false, null]') => [True, False, None]

# Objects
parse_json('{"a": 1, "b": 2}') => {"a": 1, "b": 2}
parse_json('{}') => {}

# Nested
parse_json('{"x": [1, {"y": 2}]}') => {"x": [1, {"y": 2}]}
parse_json('[{"a": 1}, {"b": 2}]') => [{"a": 1}, {"b": 2}]

# Escaped strings
parse_json('"hello\\nworld"') => "hello\nworld"
parse_json('"quote: \\\"hi\\\""') => 'quote: "hi"'

# Errors
parse_json("{}")  # unclosed object
parse_json('{"a"}')  # missing colon
parse_json("[1, 2,")  # trailing comma
```

### Output Format
Write complete Python code in `json_parser.py`. Include `parse_json(s)` function and `run_tests()`.

### Scoring
- Correctness: all tests pass
- Code quality: clean tokenizer/parser separation
- Error handling: meaningful parse errors
