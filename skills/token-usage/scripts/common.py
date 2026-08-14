"""Shared session parsing and model handling for token-usage reports."""

import gzip
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

LOCAL_TZ_NAME = "Asia/Calcutta"
LOCAL_TZ = ZoneInfo(LOCAL_TZ_NAME)


def normalize_model(model):
    """Return a stable provider/model name for pricing and reports."""
    value = (model or "unknown").strip().lower()
    aliases = {"k2.6": "kimi/k2.6", "k2.7": "kimi/k2.7", "k3": "kimi/k3"}
    return aliases.get(value, value)


def local_timestamp(timestamp):
    """Return a timestamp in local time for grouping and filtering."""
    if not timestamp:
        return ""
    try:
        value = timestamp.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(LOCAL_TZ).replace(tzinfo=None).isoformat(timespec="seconds")
    except ValueError:
        return timestamp


def local_date(timestamp):
    return local_timestamp(timestamp)[:10] if timestamp else "unknown"


def find_sessions():
    roots = [
        Path.home() / ".openclaw" / "agents" / "main" / "sessions",
        Path.home() / ".openclaw" / "agents" / "sub" / "sessions",
        Path.home() / ".openclaw" / "agents" / "main" / "agent" / "codex-home" / "sessions",
    ]
    files = []
    for root in roots:
        if root.exists():
            files.extend(root.rglob("*.jsonl"))
            files.extend(root.rglob("*.jsonl.gz"))
    return sorted(set(files))


def _model_from_context(payload):
    return payload.get("model", "") or ""


def parse_session(path):
    """Yield timestamp, normalized model, and per-turn token usage."""
    opener = gzip.open if str(path).endswith(".gz") else open
    codex_model = ""
    try:
        with opener(path, "rt", encoding="utf-8", errors="replace") as stream:
            for raw in stream:
                try:
                    record = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if record.get("type") == "turn_context":
                    codex_model = _model_from_context(record.get("payload", {})) or codex_model
                    continue
                if record.get("type") == "event_msg":
                    payload = record.get("payload", {})
                    if payload.get("type") != "token_count":
                        continue
                    usage = payload.get("info", {}).get("last_token_usage") or {}
                    if usage:
                        yield record.get("timestamp", ""), normalize_model(codex_model or "openai/gpt-5.6-luna"), {
                            "input": usage.get("input_tokens", 0),
                            "output": usage.get("output_tokens", 0),
                            "cacheRead": usage.get("cached_input_tokens", 0),
                            "cacheWrite": usage.get("cache_write_input_tokens", 0),
                        }
                    continue
                if record.get("type") != "message":
                    continue
                message = record.get("message", {})
                if message.get("role") != "assistant":
                    continue
                usage = message.get("usage") or record.get("usage")
                if usage:
                    model = message.get("model") or record.get("model") or record.get("api")
                    yield record.get("timestamp", ""), normalize_model(model), usage
    except (FileNotFoundError, OSError):
        return


def estimate_cost(usage, model, pricing):
    """Estimate cost; return None when the model has no known price."""
    rates = pricing.get(normalize_model(model))
    if rates is None:
        return None
    total = usage.get("input", 0) * (rates.get("input") or 0)
    total += usage.get("output", 0) * (rates.get("output") or 0)
    total += usage.get("cacheRead", 0) * (rates.get("cache_read") or 0)
    total += usage.get("cacheWrite", 0) * (rates.get("cache_write") or 0)
    return total / 1e6
