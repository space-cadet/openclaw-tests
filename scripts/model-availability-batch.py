#!/usr/bin/env python3
"""Run one randomized OpenClaw-harness availability batch.

The surrounding OpenClaw command cron invokes this every five minutes.  A
plain-text next-run gate adds a random 5--20 minute delay between batches.
Each model call is made through ``openclaw agent`` with no delivery flag.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "model-availability"
LOG_PATH = DATA_DIR / "runs.jsonl"
NEXT_RUN_PATH = DATA_DIR / "next-run-epoch.txt"
LOCK_PATH = DATA_DIR / ".batch.lock"
PAUSE_FILE = Path("/tmp/cron-paused")

MODELS = [
    "kimi/k2.7",
    "kimi/k2.7-code",
    "kimi/k3",
    "kimi/k3-1m",
    "deepseek/deepseek-v4-flash",
]

PROMPTS = [
    ("greeting", "Hello—are you there?"),
    ("greeting", "Hi, you there?"),
    ("greeting", "Hey—how are things?"),
    ("greeting", "Hello. Can you hear me?"),
    ("greeting", "Hi there—are you available?"),
    ("greeting", "Good morning. You around?"),
    ("greeting", "Hey, how's it going?"),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def append_event(event: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, separators=(",", ":")) + "\n")


def maintenance_event() -> None:
    append_event({
        "schema_version": 1,
        "event_type": "model_probe",
        "attempt_id": str(uuid.uuid4()),
        "observed_at": now_iso(),
        "timezone": "Asia/Kolkata",
        "harness": "openclaw",
        "scheduler_job": "availability-probe-openclaw",
        "outcome": "skipped",
        "failure_class": "maintenance_mode",
        "maintenance_skipped": True,
    })


def acquire_lock() -> bool:
    try:
        LOCK_PATH.mkdir()
        return True
    except FileExistsError:
        return False


def release_lock() -> None:
    try:
        LOCK_PATH.rmdir()
    except FileNotFoundError:
        pass


def gate_open() -> bool:
    try:
        return time.time() >= float(NEXT_RUN_PATH.read_text(encoding="utf-8").strip())
    except (FileNotFoundError, ValueError):
        return True


def set_next_gate(delay_seconds: int) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    NEXT_RUN_PATH.write_text(f"{time.time() + delay_seconds:.3f}\n", encoding="utf-8")


def classify_failure(status: str, stderr: str) -> str:
    if status == "timeout":
        return "timeout"
    text = stderr.lower()
    if "rate limit" in text or "429" in text:
        return "rate_limit"
    if "timed out" in text or "timeout" in text:
        return "timeout"
    return "harness_error"


def run_model(model: str, family: str, prompt: str, batch_id: str) -> None:
    started = time.monotonic()
    attempt_id = str(uuid.uuid4())
    session_key = f"agent:main:availability-{batch_id}-{model.replace('/', '-')}-{attempt_id[:8]}"
    command = [
        "openclaw", "agent", "--agent", "main", "--model", model,
        "--session-key", session_key, "--message", prompt,
        "--json", "--timeout", "45",
    ]
    event = {
        "schema_version": 1,
        "event_type": "model_probe",
        "attempt_id": attempt_id,
        "batch_id": batch_id,
        "observed_at": now_iso(),
        "timezone": "Asia/Kolkata",
        "provider": model.split("/", 1)[0],
        "model": model,
        "harness": "openclaw",
        "probe_profile": "casual-conversation-v1",
        "task_family": family,
        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "outcome": "failure",
        "failure_class": "unknown",
        "latency_ms": None,
        "retry_count": 0,
        "scheduler_job": "availability-probe-openclaw",
        "host_class": "local",
        "maintenance_skipped": False,
    }
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        event["latency_ms"] = round((time.monotonic() - started) * 1000)
        parsed = None
        # OpenClaw may print startup warnings before a pretty-printed JSON
        # object. Decode the first complete object rather than one line.
        decoder = json.JSONDecoder()
        object_start = result.stdout.find("{")
        if object_start >= 0:
            try:
                parsed, _ = decoder.raw_decode(result.stdout[object_start:])
            except json.JSONDecodeError:
                parsed = None
        if parsed:
            meta = parsed.get("result", {}).get("meta", {})
            agent_meta = meta.get("agentMeta", {})
            error = parsed.get("error") if isinstance(parsed.get("error"), dict) else {}
            event.update({
                "outcome": "success" if parsed.get("status") == "ok" else "failure",
                "failure_class": None if parsed.get("status") == "ok" else "harness_error",
                "run_id": parsed.get("runId"),
                "provider": agent_meta.get("provider", event["provider"]),
                "model": agent_meta.get("model", model),
                "latency_ms": meta.get("durationMs", event["latency_ms"]),
                "input_tokens": agent_meta.get("usage", {}).get("input"),
                "output_tokens": agent_meta.get("usage", {}).get("output"),
                "cache_read_tokens": agent_meta.get("usage", {}).get("cacheRead"),
                "cache_write_tokens": agent_meta.get("usage", {}).get("cacheWrite"),
                "total_tokens": agent_meta.get("usage", {}).get("total"),
                "stop_reason": meta.get("stopReason"),
                "fallback_used": parsed.get("result", {}).get("meta", {}).get("executionTrace", {}).get("fallbackUsed", False),
                "error_code": error.get("code"),
                "error_type": error.get("type"),
            })
        else:
            event["failure_class"] = classify_failure("error", result.stderr)
            event["exit_code"] = result.returncode
    except subprocess.TimeoutExpired:
        event["latency_ms"] = round((time.monotonic() - started) * 1000)
        event["failure_class"] = "timeout"
    except OSError as exc:
        event["failure_class"] = "local_resource"
        event["error_type"] = type(exc).__name__
    append_event(event)


def main() -> int:
    if PAUSE_FILE.exists():
        maintenance_event()
        return 0
    if not gate_open() or not acquire_lock():
        return 0
    try:
        batch_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
        family, prompt = random.choice(PROMPTS)
        models = MODELS[:]
        random.shuffle(models)
        for model in models:
            run_model(model, family, prompt, batch_id)
        set_next_gate(random.randint(5 * 60, 20 * 60))
        return 0
    finally:
        release_lock()


if __name__ == "__main__":
    sys.exit(main())
