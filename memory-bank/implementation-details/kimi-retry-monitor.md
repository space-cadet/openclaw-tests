# Kimi Retry Storm Monitor

*Created: 2026-08-17*
*Task: T12*

## Problem

OpenClaw users on Kimi models (especially k3, k2p6) frequently encounter:

> ⚠️ All models are temporarily rate-limited. Please try again in a few minutes.

The hypothesis: OpenClaw's harness may be retrying requests rapidly when models fail, causing a **retry storm** that makes the rate-limiting worse. We need objective data to confirm or reject this.

## Solution Architecture

### v1: `lsof` approach (ABANDONED)

Initial attempt used `lsof -nP -iTCP | grep agent-gw.kimi.com` to count active connections.

**Why it failed:** On macOS, `lsof` displays resolved IP addresses, not hostnames:
```
node  41593  sage  43u  IPv4  ...  TCP 10.2.0.2:55069->104.18.20.246:443 (ESTABLISHED)
```

The `agent-gw.kimi.com` hostname is resolved to Cloudflare IPs before the connection is established, so hostname-based filtering returns zero matches.

**Alternatives considered:**
- PID-based filtering (`lsof -p <gateway_pid>`) — captures all gateway HTTPS traffic, not just Kimi
- DNS resolution + IP matching — fragile (IPs change)
- `nettop` / `netstat` — macOS-specific, complex parsing

### v2: Gateway log tail (ADOPTED)

OpenClaw's gateway writes structured log lines for every model request:

```
2026-08-17T11:26:02.418+05:30 [provider-transport-fetch] [model-fetch] start provider=kimi api=anthropic-messages model=k2.7 method=POST url=https://agent-gw.kimi.com/coding/v1/messages
2026-08-17T11:26:13.491+05:30 [provider-transport-fetch] [model-fetch] response provider=kimi api=anthropic-messages model=k2.7 status=200 elapsedMs=11068
```

The monitor tails this log and parses:
- **Request starts** → increment in-flight counter
- **Responses** → decrement in-flight, record status code
- **429 status** → log ALERT
- **Burst patterns** → log BURST when thresholds exceeded

**Advantages over `lsof`:**
- Exact model names (k2.7, k3, etc.)
- Exact HTTP status codes
- No root privileges needed
- Works across platforms (macOS/Linux)
- Zero network overhead

## Implementation

### Script: `scripts/kimi-retry-monitor.sh`

**Commands:**
| Command | Purpose |
|---------|---------|
| `start` | Start daemon (subshell + disown) |
| `stop` | Stop daemon |
| `status` | Show PID + recent log tail |
| `run` | Run in foreground (for LaunchAgent/debug) |
| `check [N]` | Analyze last N minutes, produce verdict |

**Burst detection thresholds:**
- `BURST_THRESHOLD=3` — in-flight requests to trigger burst alert
- `RAPID_COUNT=4` — requests in `RAPID_WINDOW_SEC=10` to count as rapid-fire

**Log rotation:**
- Hourly files: `~/.openclaw/logs/kimi-monitor/YYYYMMDD_HH.log`
- Auto-delete after 24 hours

### macOS LaunchAgent: `launchd/ai.openclaw.kimi-retry-monitor.plist`

- Runs `kimi-retry-monitor.sh run` at login
- `KeepAlive` with `SuccessfulExit=false` respawns on crash
- Stdout/stderr to `~/.openclaw/logs/kimi-monitor/launchd.*.log`

**Installation:**
```bash
cp launchd/ai.openclaw.kimi-retry-monitor.plist ~/Library/LaunchAgents/
# Auto-starts on next login. For immediate start:
launchctl load ~/Library/LaunchAgents/ai.openclaw.kimi-retry-monitor.plist
```

## Verdict Logic

The `check` command produces one of four verdicts:

| Burst | 429 | Verdict |
|-------|-----|---------|
| Yes | Yes | ⚠️ RETRY STORM LIKELY — bursts + rate-limit responses |
| Yes | No | ⚠️ BURSTS WITHOUT REJECTION — rapid requests, no 429s |
| No | Yes | ⚠️ RATE-LIMIT WITHOUT BURST — API-side throttling |
| No | No | ✅ NO ISSUES — no detectable retry activity |

## Early Findings (2026-08-17)

First `check` run revealed **10 HTTP 429 responses** from Kimi in a single day:

| Time (IST) | Model | Status |
|------------|-------|--------|
| 05:27 | k3 | 429 |
| 06:15 | k3 | 429 |
| 08:32 | k3 | 429 |
| 09:07 | k3 | 429 (×2) |
| 09:10 | k3 | 429 |
| 09:27 | k3 | 429 |
| 09:48 | k3 | 429 |
| 09:50 | k3 | 429 |
| 11:18 | k2p6 | 429 |

**Pattern:** All 429s on k3 and k2p6. Zero on k2.7. This correlates with user reports that rate limits are model-dependent.

## Future Improvements

1. **Cross-provider support** — Make the `provider=kimi` pattern configurable
2. **Dashboard integration** — Feed monitor data into the T11 availability study JSONL
3. **Alert delivery** — Optional Telegram notification when burst detected
4. **Gateway log path detection** — Auto-detect macOS vs Linux log locations

## Files

- `scripts/kimi-retry-monitor.sh`
- `launchd/ai.openclaw.kimi-retry-monitor.plist`
- `memory-bank/tasks/T12.md`
- `memory-bank/implementation-details/kimi-retry-monitor.md` (this file)
