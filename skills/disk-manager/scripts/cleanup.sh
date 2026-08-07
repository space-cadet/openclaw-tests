#!/bin/bash
# cleanup.sh — Safe cleanup operations with logging
# Sources log.sh for operation tracking

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/log.sh"

echo "=== VPS Disk Cleanup ==="
echo "Current usage: $(df -h / | awk 'NR==2 {print $5}')"
echo ""

# Step 1: APT cleanup
echo "Step 1: APT cleanup..."
log-apt-clean

# Step 2: npm cache
echo "Step 2: npm cache..."
BEFORE=$(du -sh ~/.npm 2>/dev/null | cut -f1)
npm cache clean --force 2>/dev/null
AFTER=$(du -sh ~/.npm 2>/dev/null | cut -f1)
log_op "NPM_CACHE_CLEAN" "~/.npm" "$BEFORE -> $AFTER" "routine cleanup"

# Step 3: Docker prune (if available)
if command -v docker &> /dev/null; then
    echo "Step 3: Docker prune..."
    log-docker-prune
fi

# Step 4: Journal vacuum
echo "Step 4: Journal vacuum (7 days)..."
JOURNAL_BEFORE=$(journalctl --disk-usage 2>/dev/null | head -1)
journalctl --vacuum-time=7d 2>/dev/null
JOURNAL_AFTER=$(journalctl --disk-usage 2>/dev/null | head -1)
log_op "JOURNAL_VACUUM" "/var/log/journal" "$JOURNAL_BEFORE -> $JOURNAL_AFTER" "routine cleanup"

echo ""
echo "=== After cleanup ==="
df -h /
