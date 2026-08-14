#!/usr/bin/env python3
"""Parse OpenClaw session JSONL files and aggregate token usage."""

import json
import gzip
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("Asia/Calcutta")
import argparse
import re
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import glob
from common import find_sessions as find_shared_sessions, parse_session as parse_shared_session, normalize_model

DEFAULT_PRICING = {
    "kimi/k2.7": {"input": 0.50, "output": 2.00, "cache_read": 0.10, "cache_write": 1.00},
    "anthropic/claude-sonnet-4-5": {"input": 3.00, "output": 15.00, "cache_read": 0.30, "cache_write": 3.75},
    "openai/gpt-4o": {"input": 2.50, "output": 10.00, "cache_read": 1.25, "cache_write": 0},
    "openai/gpt-4o-mini": {"input": 0.15, "output": 0.60, "cache_read": 0.075, "cache_write": 0},
}

def load_pricing():
    pricing_file = Path(__file__).parent / "pricing.json"
    if pricing_file.exists():
        with open(pricing_file) as f:
            return {**DEFAULT_PRICING, **json.load(f)}
    return DEFAULT_PRICING

def find_sessions(base_paths=None):
    if base_paths is None:
        return [str(path) for path in find_shared_sessions()]
    if base_paths is None:
        base_paths = [
            Path.home() / ".openclaw" / "agents" / "main" / "sessions",
            Path.home() / ".openclaw" / "agents" / "sub" / "sessions",
            Path.home() / ".openclaw" / "agents" / "main" / "agent" / "codex-home" / "sessions",
        ]
    sessions = []
    for bp in base_paths:
        if bp.exists():
            sessions.extend(glob.glob(str(bp / "**" / "*.jsonl"), recursive=True))
            sessions.extend(glob.glob(str(bp / "**" / "*.jsonl.gz"), recursive=True))
    return sorted(set(sessions))

def parse_session_file(path):
    """Yield (timestamp, model, usage_dict) for each assistant message."""
    yield from parse_shared_session(path)
    return
    # Kept below only as a reference for old session formats.
    open_fn = gzip.open if path.endswith(".gz") else open
    try:
        with open_fn(path, "rt", encoding="utf-8", errors="replace") as f:
            codex_model = ""
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if msg.get("type") == "event_msg":
                    payload = msg.get("payload", {})
                    if payload.get("type") == "token_count":
                        usage = (payload.get("info", {}).get("last_token_usage") or {})
                        if usage:
                            yield msg.get("timestamp", ""), codex_model or "openai/gpt-5.6-luna", {
                                "input": usage.get("input_tokens", 0),
                                "output": usage.get("output_tokens", 0),
                                "cacheRead": usage.get("cached_input_tokens", 0),
                                "cacheWrite": usage.get("cache_write_input_tokens", 0),
                            }
                    continue
                if msg.get("type") == "turn_context":
                    codex_model = msg.get("payload", {}).get("model", "") or codex_model
                    continue
                if msg.get("type") != "message":
                    continue
                m = msg.get("message", {})
                if m.get("role") != "assistant":
                    continue
                usage = m.get("usage") or msg.get("usage")
                if not usage:
                    continue
                ts = msg.get("timestamp", "")
                model = m.get("model", msg.get("model", msg.get("api", "")))
                yield ts, model, usage
    except (FileNotFoundError, OSError):
        pass

def aggregate(sessions, since=None, until=None):
    by_day = defaultdict(lambda: defaultdict(lambda: {
        "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "messages": 0
    }))
    by_session = defaultdict(lambda: {
        "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "messages": 0, "models": set()
    })
    
    for spath in sessions:
        sid = Path(spath).stem
        for ts, model, usage in parse_session_file(spath):
            if since and ts < since:
                continue
            if until and ts > until:
                continue
            day = ts[:10] if ts else "unknown"
            model_key = model or "unknown"
            
            inp = usage.get("input", 0)
            out = usage.get("output", 0)
            
            d = by_day[day][model_key]
            d["input"] += inp
            d["output"] += out
            d["cacheRead"] += usage.get("cacheRead", 0)
            d["cacheWrite"] += usage.get("cacheWrite", 0)
            d["messages"] += 1
            
            s = by_session[sid]
            s["input"] += inp
            s["output"] += out
            s["cacheRead"] += usage.get("cacheRead", 0)
            s["cacheWrite"] += usage.get("cacheWrite", 0)
            s["messages"] += 1
            s["models"].add(model_key)
    
    return by_day, by_session

def detect_cron_job(path):
    """Extract cron job ID and name from first user message in session."""
    open_fn = gzip.open if path.endswith(".gz") else open
    try:
        with open_fn(path, "rt", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if msg.get("type") != "message":
                    continue
                m = msg.get("message", {})
                if m.get("role") != "user":
                    continue
                content = m.get("content", [])
                text = ""
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "text":
                        text += c.get("text", "")
                match = re.search(r'\[cron:([a-f0-9\-]+)\s+([^\]]+)\]', text)
                if match:
                    return match.group(1), match.group(2).strip()
                match2 = re.search(r'\[cron:([a-z0-9\-]+)\s+([^\]]+)\]', text)
                if match2:
                    return match2.group(1), match2.group(2).strip()
                break
    except Exception:
        pass
    return None, None

def aggregate_by_cron(sessions, since=None, until=None):
    """Aggregate token usage by cron job and date."""
    by_day_job = defaultdict(lambda: {
        "input": 0, "output": 0, "messages": 0, "name": ""
    })
    
    for spath in sessions:
        job_id, job_name = detect_cron_job(spath)
        if not job_id:
            continue
        for ts, model, usage in parse_session_file(spath):
            if since and ts < since:
                continue
            if until and ts > until:
                continue
            day = ts[:10] if ts else "unknown"
            key = f"{day}:{job_id}"
            
            inp = usage.get("input", 0)
            out = usage.get("output", 0)
            
            by_day_job[key]["input"] += inp
            by_day_job[key]["output"] += out
            by_day_job[key]["messages"] += 1
            if job_name and not by_day_job[key]["name"]:
                by_day_job[key]["name"] = job_name
    
    return by_day_job

def estimate_cost(usage, model, pricing):
    """Estimate cost in USD. Prices are per 1M tokens."""
    model = normalize_model(model)
    p = pricing.get(model)
    if p is None and "/" not in model:
        p = pricing.get(f"kimi/{model}")
    if p is None:
        return 0.0
    cost = 0.0
    cost += usage.get("input", 0) * (p.get("input") or 0) / 1e6
    cost += usage.get("output", 0) * (p.get("output") or 0) / 1e6
    cost += usage.get("cacheRead", 0) * (p.get("cache_read") or 0) / 1e6
    cost += usage.get("cacheWrite", 0) * (p.get("cache_write") or 0) / 1e6
    return cost

def format_report(by_day, by_session, pricing=None, costs=False):
    lines = []
    total = {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "messages": 0, "cost": 0.0}
    
    for day in sorted(by_day.keys(), reverse=True):
        lines.append(f"\n## {day}")
        day_total = {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "messages": 0, "cost": 0.0}
        for model in sorted(by_day[day].keys()):
            u = by_day[day][model]
            usage_for_cost = {"input": u["input"], "output": u["output"], "cacheRead": u["cacheRead"], "cacheWrite": u["cacheWrite"]}
            c = estimate_cost(usage_for_cost, model, pricing) if (costs and pricing) else 0.0
            lines.append(f"  {model:30s}  in={u['input']:>10,}  out={u['output']:>8,}  cache={u['cacheRead']:>8,}  msgs={u['messages']:>4}")
            if costs and pricing:
                lines.append(f"{'':34s}est. ${c:.4f}")
            for k in ["input", "output", "cacheRead", "cacheWrite", "messages"]:
                day_total[k] += u[k]
            day_total["cost"] += c
            for k in ["input", "output", "cacheRead", "cacheWrite", "messages"]:
                total[k] += u[k]
            total["cost"] += c
        lines.append(f"  {'Day total':30s}  in={day_total['input']:>10,}  out={day_total['output']:>8,}  msgs={day_total['messages']:>4}")
        if costs and pricing:
            lines.append(f"  {'':34s}est. ${day_total['cost']:.4f}")
    
    lines.append(f"\n## Grand Total")
    lines.append(f"  input={total['input']:,}  output={total['output']:,}  messages={total['messages']:,}")
    if costs and pricing:
        lines.append(f"  est. cost=${total['cost']:.4f}")
    
    return "\n".join(lines)

def format_cron_report(by_day_job, pricing=None, costs=False):
    lines = []
    total = {"input": 0, "output": 0, "messages": 0, "cost": 0.0}
    
    days = defaultdict(dict)
    for key, data in by_day_job.items():
        day, job_id = key.split(":", 1)
        days[day][job_id] = data
    
    for day in sorted(days.keys(), reverse=True):
        lines.append(f"\n## {day}")
        day_total = {"input": 0, "output": 0, "messages": 0, "cost": 0.0}
        
        jobs = sorted(days[day].items(), 
                     key=lambda x: x[1]["input"] + x[1]["output"], 
                     reverse=True)
        
        for job_id, data in jobs:
            name = data.get("name", job_id[:8])
            if len(name) > 28:
                name = name[:25] + "..."
            
            usage_for_cost = {"input": data["input"], "output": data["output"], "cacheRead": 0, "cacheWrite": 0}
            c = estimate_cost(usage_for_cost, "kimi/k2.7", pricing) if (costs and pricing) else 0.0
            
            lines.append(f"  {name:<28}  calls={data['messages']:>4}  in={data['input']:>10,}  out={data['output']:>8,}")
            if costs and pricing:
                lines.append(f"{'':34s}est. ${c:.4f}")
            
            for k in ["input", "output", "messages"]:
                day_total[k] += data[k]
            day_total["cost"] += c
            for k in ["input", "output", "messages"]:
                total[k] += data[k]
            total["cost"] += c
        
        lines.append(f"  {'DAY TOTAL':<28}  calls={day_total['messages']:>4}  in={day_total['input']:>10,}  out={day_total['output']:>8,}")
        if costs and pricing:
            lines.append(f"  {'':34s}est. ${day_total['cost']:.4f}")
    
    lines.append(f"\n## Grand Total")
    lines.append(f"  input={total['input']:,}  output={total['output']:,}  messages={total['messages']:,}")
    if costs and pricing:
        lines.append(f"  est. cost=${total['cost']:.4f}")
    
    return "\n".join(lines)

def to_json(by_day, by_session, pricing=None):
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "days": {},
        "sessions": {}
    }
    for day, models in by_day.items():
        out["days"][day] = {}
        for model, u in models.items():
            d = dict(u)
            if pricing:
                usage_for_cost = {"input": u["input"], "output": u["output"], "cacheRead": u["cacheRead"], "cacheWrite": u["cacheWrite"]}
                d["estimated_cost_usd"] = round(estimate_cost(usage_for_cost, model, pricing), 6)
            out["days"][day][model] = d
    for sid, s in by_session.items():
        out["sessions"][sid] = {
            **{k: s[k] for k in ["input", "output", "cacheRead", "cacheWrite", "messages"]},
            "models": list(s["models"])
        }
    return out

def to_cron_json(by_day_job, pricing=None):
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "days": {}
    }
    for key, data in by_day_job.items():
        day, job_id = key.split(":", 1)
        if day not in out["days"]:
            out["days"][day] = {}
        d = {
            "name": data.get("name", ""),
            "input": data["input"],
            "output": data["output"],
            "messages": data["messages"]
        }
        if pricing:
            usage_for_cost = {"input": data["input"], "output": data["output"], "cacheRead": 0, "cacheWrite": 0}
            d["estimated_cost_usd"] = round(estimate_cost(usage_for_cost, "kimi/k2.7", pricing), 6)
        out["days"][day][job_id] = d
    return out

def main():
    parser = argparse.ArgumentParser(description="Track OpenClaw token usage")
    parser.add_argument("--yesterday", action="store_true", help="Report for yesterday only")
    parser.add_argument("--today", action="store_true", help="Report for today only")
    parser.add_argument("--week", action="store_true", help="Report for last 7 days")
    parser.add_argument("--all", action="store_true", help="Report all time")
    parser.add_argument("--by-model", action="store_true", help="Group by model")
    parser.add_argument("--by-cron", action="store_true", help="Group by cron job")
    parser.add_argument("--costs", action="store_true", help="Estimate costs")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--sessions", nargs="*", help="Specific session files")
    args = parser.parse_args()
    
    now = datetime.now(LOCAL_TZ)
    since = None
    until = None
    
    if args.today:
        since = now.strftime("%Y-%m-%dT00:00:00")
    elif args.yesterday:
        yesterday = now - timedelta(days=1)
        since = yesterday.strftime("%Y-%m-%dT00:00:00")
        until = now.strftime("%Y-%m-%dT00:00:00")
    elif args.week:
        since = (now - timedelta(days=7)).strftime("%Y-%m-%dT00:00:00")
    elif not args.all:
        args.today = True
        since = now.strftime("%Y-%m-%dT00:00:00")
    
    sessions = args.sessions or find_sessions()
    if not sessions:
        print("No session files found.")
        return
    
    pricing = load_pricing() if args.costs else None
    
    if args.by_cron:
        by_day_job = aggregate_by_cron(sessions, since=since, until=until)
        if args.json:
            print(json.dumps(to_cron_json(by_day_job, pricing), indent=2))
        else:
            print(format_cron_report(by_day_job, pricing, args.costs))
    else:
        by_day, by_session = aggregate(sessions, since=since, until=until)
        if args.json:
            print(json.dumps(to_json(by_day, by_session, pricing), indent=2))
        else:
            print(format_report(by_day, by_session, pricing, args.costs))

if __name__ == "__main__":
    main()
