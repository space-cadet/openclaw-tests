---
name: disk-manager
description: "VPS disk audit and cleanup with persistent operation logging. Deeper than basic disk-check skills."
metadata:
  keywords: [disk, cleanup, audit, space, usage, vps, maintenance]
  version: "1.0.0"
  author: "cloudy"
  license: "MIT"
---

# Disk Manager

Use when the user mentions disk space, cleanup, "running low on space", "disk full", or asks for a VPS audit. This skill provides deeper analysis than basic `df -h` checks.

## When to Use

- User says "disk is full", "low on space", "cleanup", "audit disk"
- Disk usage >85% (check via `df -h`)
- Periodic maintenance (monthly/quarterly)
- Before installing large packages or services

## When NOT to Use

- User wants to check a specific file or directory size only
- User wants to monitor ongoing (use `system-info` or Netdata instead)

## Workflow

1. **Audit** — Run comprehensive analysis (see `scripts/audit.sh`)
   - Full filesystem tree (`du -sh /*`, `/home/*`, `/var/*`, `/usr/*`)
   - Large files (`find /home -type f -size +50M`)
   - Inode usage (`df -i`)
   - Process impact (RAM per service)
   - Package ecosystems (snap, docker, npm caches)

2. **Analyze** — Identify cleanup targets
   - Safe: caches, temp files, old logs, disabled packages
   - Review: old code projects, unused browser binaries
   - Dangerous: live data, user files (ask first)

3. **Clean** — Execute with logging (see `scripts/cleanup.sh`)
   - Always log operations to `logs/file-operations.log`
   - Show before/after sizes
   - Update memory-bank task T78

4. **Report** — Generate markdown report
   - Save to `reference/vps-disk-usage-YYYY-MM-DD.md`
   - Include: summary, breakdown tables, recommendations, historical trend

## Safety Rules

- **NEVER** delete user data without explicit confirmation
- **ALWAYS** log deletions with timestamp, user, size, reason
- **ALWAYS** show what will be deleted and total size before removing
- Focus on caches, temp files, disabled packages first
- Run `df -h` before and after cleanup to verify

## Key Commands

```bash
# Quick check
df -h && du -sh /* 2>/dev/null | sort -rh | head -10

# Full audit (run as subagent for responsiveness)
bash ~/.openclaw/workspace/skills/disk-manager/scripts/audit.sh

# Logged cleanup
source ~/.openclaw/workspace/skills/disk-manager/scripts/log.sh
safe-rm /path/to/target "reason for deletion"
log-apt-clean
```

## Outputs

- **Audit report:** `reference/vps-disk-usage-YYYY-MM-DD.md`
- **Operation log:** `logs/file-operations.log`
- **Task tracker:** `memory-bank/tasks/T78.md`

## Related

- **T78** (memory-bank): VPS Disk Usage Audit & Cleanup task
- **System Info** (ClawHub): Lightweight monitoring (`df -h`, `free -h`)
- **Temp Cleaner** (ClawHub): Simple temp/cache removal
- **Netdata**: Real-time monitoring (install separately)
