# Implementation Details: cron-management

## Architecture

The cron-management skill provides a thin CLI wrapper around the `openclaw cron` API, plus a filesystem-based maintenance mode that works independently of OpenClaw.

### Two-Layer Design

```
┌─────────────────────────────────────────┐
│  Layer 1: OpenClaw API (normal ops)     │
│  - cronctl pause/resume <name>          │
│  - cronctl pause-all/resume-all         │
│  - cronctl status/health                │
│  Uses: openclaw cron list/get/update    │
└─────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────┐
│  Layer 2: Filesystem Flag (emergency)   │
│  - cronctl maintenance on|off           │
│  - /tmp/cron-paused                     │
│  Works even if OpenClaw is down         │
└─────────────────────────────────────────┘
```

### Why Two Layers?

**Layer 1 (API)** is for normal operations:
- Graceful enable/disable
- Preserves job state in OpenClaw config
- Can target individual jobs
- Required for `status` and `health` reporting

**Layer 2 (Filesystem)** is for emergencies:
- Works when OpenClaw is down or unresponsive
- Instant — no API calls
- Global — affects all jobs that check the flag
- Survives reboots (well, `/tmp` doesn't, but the concept does)

## Maintenance Mode Integration

### For Shell-Based Cron Jobs

Add at the top of any shell script:

```bash
#!/bin/bash
set -euo pipefail

# Maintenance mode check
if [ -f /tmp/cron-paused ]; then
  echo "$(date -Iseconds) — $(basename "$0") skipped (maintenance mode)" >> /tmp/cron-skipped.log
  exit 0
fi

# ... rest of script
```

### For OpenClaw agentTurn Payloads

Add to the beginning of the message text:

```
If /tmp/cron-paused exists, reply NO_REPLY and exit immediately.
```

Example payload structure:
```json
{
  "kind": "agentTurn",
  "message": "Task Name\n\nIf /tmp/cron-paused exists, reply NO_REPLY and exit immediately.\n\nSteps:\n1. Do thing\n2. Do other thing",
  "model": "kimi/k2.7"
}
```

### For Python Scripts

```python
import os
import sys
from datetime import datetime

PAUSE_FILE = "/tmp/cron-paused"
SKIP_LOG = "/tmp/cron-skipped.log"

def check_maintenance_mode():
    if os.path.exists(PAUSE_FILE):
        with open(SKIP_LOG, "a") as f:
            f.write(f"{datetime.now().isoformat()} — {sys.argv[0]} skipped (maintenance mode)\n")
        sys.exit(0)

check_maintenance_mode()
# ... rest of script
```

### For Node.js Scripts

```javascript
const fs = require('fs');
const path = require('path');

const PAUSE_FILE = '/tmp/cron-paused';
const SKIP_LOG = '/tmp/cron-skipped.log';

function checkMaintenanceMode() {
  if (fs.existsSync(PAUSE_FILE)) {
    const entry = `${new Date().toISOString()} — ${path.basename(process.argv[1])} skipped (maintenance mode)\n`;
    fs.appendFileSync(SKIP_LOG, entry);
    process.exit(0);
  }
}

checkMaintenanceMode();
// ... rest of script
```

## Rollout Strategy

### New Jobs
All new cron jobs should include the maintenance mode check at the top of their payload.

### Existing Jobs
Update existing jobs incrementally:
1. Start with jobs that run frequently (every 30 min, hourly)
2. Then daily jobs
3. Finally weekly/monthly jobs

Use `cronctl pause <name>` to temporarily disable a job while updating its payload, then `cronctl resume <name>`.

### Verification
After adding maintenance checks:
```bash
# Enable maintenance mode
cronctl maintenance on

# Wait for next job trigger, check log
tail -f /tmp/cron-skipped.log

# Should see entries like:
# 2026-07-20T05:30:00+05:30 — check-mail.sh skipped (maintenance mode)

# Disable maintenance mode
cronctl maintenance off
```

## Job Naming Conventions

The `cronctl` script uses fuzzy matching for job names:

```bash
cronctl pause blog        # Matches "cloudy-blog-writer"
cronctl pause memory      # Matches "graph-memory-queue-sync"
cronctl pause beads       # Matches "beads-executor"
```

Name jobs descriptively so fuzzy matching works well:
- ✅ `cloudy-blog-writer` — searchable by "blog"
- ✅ `graph-memory-queue-sync` — searchable by "memory"
- ❌ `job-7` — not searchable

## Error Handling

### API Errors
If `openclaw cron list` fails (gateway down, auth error):
- `cronctl list` → dies with error message
- `cronctl maintenance` → still works (filesystem layer)

### Partial Failures
`pause-all` and `resume-all` use `|| true` per job, so one failure doesn't abort the batch:

```bash
echo "$jobs_json" | jq -r '.jobs[] | select(.enabled) | .id' | while read -r id; do
  openclaw cron update "$id" '{"enabled": false}' 2>/dev/null || true
done
```

## State Files

| File | Purpose | Persistence |
|------|---------|-------------|
| `/tmp/cron-paused` | Maintenance mode flag | Lost on reboot |
| `/tmp/cron-skipped.log` | Log of skipped jobs | Lost on reboot |

For persistent maintenance mode across reboots, use `/var/run/cron-paused` or a systemd service that creates the flag on boot.

## Security

- `/tmp/cron-paused` is world-writable — any user can create/remove it
- In multi-user environments, use `/var/run/cron-paused` with appropriate permissions
- The maintenance check should be the FIRST thing in a job payload, before any network calls or file operations

## Future Enhancements

- [ ] Tag-based operations: `cronctl pause --tag blog` to pause all blog-related jobs
- [ ] Dry-run mode: `cronctl pause-all --dry-run` to preview without changing
- [ ] Config file: `~/.config/cronctl/config.json` for default settings
- [ ] Persistent maintenance mode across reboots via systemd
- [ ] Integration with Healthchecks.io for external monitoring

## Availability Study Integration

The provider/model availability study uses the existing management contract:

- Job name: `availability-probe-openclaw`
- Kind: silent OpenClaw command job
- Schedule: every 5 minutes, with the runner enforcing a random 5--20 minute gate between batches
- Delivery: disabled (`mode: none`); individual probe outcomes never notify Telegram
- Pause behavior: the runner checks `/tmp/cron-paused` before network calls and records maintenance skips locally
- Health control: `cronctl list`, `cronctl pause availability-probe-openclaw`, `cronctl resume availability-probe-openclaw`, and `cronctl health availability-probe-openclaw`

The runner is implemented in `scripts/model-availability-batch.py`. It writes local JSONL runtime data and uses a lock to prevent overlapping batches. Aggregate reporting jobs are intentionally separate and may opt into user-facing delivery.
