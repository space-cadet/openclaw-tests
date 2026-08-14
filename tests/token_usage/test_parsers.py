import json
import tempfile
import unittest
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).parents[2] / "skills" / "token-usage" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from common import parse_session


class ParserTests(unittest.TestCase):
    def write_records(self, records):
        handle = tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False)
        with handle:
            for record in records:
                handle.write(json.dumps(record) + "\n")
        return Path(handle.name)

    def test_openclaw_message(self):
        path = self.write_records([{
            "type": "message",
            "timestamp": "2026-08-14T10:00:00Z",
            "message": {"role": "assistant", "model": "k3", "usage": {"input": 10, "output": 4}},
        }])
        try:
            rows = list(parse_session(path))
            self.assertEqual(rows[0][1], "kimi/k3")
            self.assertEqual(rows[0][2]["input"], 10)
        finally:
            path.unlink()

    def test_codex_token_count(self):
        path = self.write_records([
            {"type": "turn_context", "payload": {"model": "gpt-5.6-luna"}},
            {"type": "event_msg", "timestamp": "2026-08-14T10:00:00Z", "payload": {
                "type": "token_count",
                "info": {"last_token_usage": {"input_tokens": 20, "output_tokens": 5, "cached_input_tokens": 8}},
            }},
        ])
        try:
            rows = list(parse_session(path))
            self.assertEqual(rows[0][1], "gpt-5.6-luna")
            self.assertEqual(rows[0][2]["cacheRead"], 8)
        finally:
            path.unlink()


if __name__ == "__main__":
    unittest.main()
