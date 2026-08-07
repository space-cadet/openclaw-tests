# Disk Manager Skill

**Location:** `skills/disk-manager/`  
**Category:** System / Monitoring  
**Version:** 1.0.0

## What It Does

Comprehensive VPS disk audit and cleanup system. Goes deeper than basic `df -h` checks or simple temp cleaners.

### Key Differences from ClawHub Skills

| Feature | ClawHub Disk Cleanup | This Skill |
|---------|---------------------|------------|
| Analysis depth | Top 10 in `~` | Full filesystem tree (`/`, `/home`, `/var`, `/usr`) |
| Large files | >100M only | >50M, sorted by directory |
| Inode tracking | No | Yes (`df -i`) |
| Package ecosystems | npm, pip, docker | **+ apt, pnpm, snap, journal** |
| Operation logging | No | **Persistent audit trail** |
| Historical tracking | No | **Memory-bank integration (T78)** |
| Report generation | No | **Markdown reports** |
| Service impact analysis | No | **Per-process RAM tracking** |

## Structure

```
disk-manager/
├── SKILL.md              # Skill definition & trigger rules
└── scripts/
    ├── audit.sh          # Comprehensive disk audit
    ├── cleanup.sh        # Safe cleanup with logging
    └── log.sh            # Operation logging utilities
```

## Usage

### Quick Check
```bash
df -h && du -sh /* 2>/dev/null | sort -rh | head -10
```

### Full Audit
```bash
# Run as subagent for responsiveness
bash ~/.openclaw/workspace/skills/disk-manager/scripts/audit.sh

# Report saved to: reference/vps-disk-usage-YYYY-MM-DD.md
```

### Cleanup with Logging
```bash
source ~/.openclaw/workspace/skills/disk-manager/scripts/log.sh

# Safe delete with logging
safe-rm /path/to/old-backup "Removing outdated backup"

# APT cleanup with logging
log-apt-clean

# Show recent operations
show-ops 20

# Generate markdown report
export-ops-report
```

## Safety

- **Never** deletes user data without explicit confirmation
- **Always** logs deletions with timestamp, user, size, reason
- Focuses on caches, temp files, disabled packages first
- Shows before/after `df -h` for verification

## Integration

- **T78** (memory-bank): Tracks disk usage over time
- **logs/file-operations.log**: Persistent operation audit trail
- **reference/**: Generated markdown audit reports

## When to Use vs. Other Skills

| Scenario | Use This | Use ClawHub |
|----------|----------|-------------|
| "Disk is full" | ✅ Yes | ⚠️ Basic check only |
| "Deep audit" | ✅ Yes | ❌ No |
| "Track cleanup history" | ✅ Yes | ❌ No |
| "Quick temp cleanup" | ✅ Yes | ✅ Yes |
| "Sandboxed safety" | ⚠️ Direct execution | ✅ Docker sandbox |
| "Community updates" | Local only | ✅ Auto-updated |

## ClawHub Equivalents

- [Disk Cleanup](https://openclawlaunch.com/skills/disk-cleanup) — Lightweight, sandboxed
- [Temp Cleaner](https://openclawlaunch.com/skills/temp-cleaner) — Temp files only
- [System Info](https://openclawlaunch.com/skills/system-info) — Basic monitoring

Our skill is **complementary**: use ClawHub for quick checks, use this for deep audits and persistent tracking.

## Future: Publishing to ClawHub

To publish:
1. Sanitize paths (remove `quantumofgravity.com` references)
2. Add Docker sandbox wrapper
3. Submit to [ClawHub](https://openclawlaunch.com/skills)

**Recommendation:** Keep local version for production use (full system access, persistent logs). Publish simplified version to ClawHub for broader community.
