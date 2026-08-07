#!/bin/bash
# file-ops-log.sh — Log file management operations for audit trail
# Usage: source this script or run commands through it

LOG_DIR="/home/cloudy/.openclaw/workspace/logs"
LOG_FILE="$LOG_DIR/file-operations.log"
mkdir -p "$LOG_DIR"

# Function to log an operation
log_op() {
    local op="$1"
    local target="$2"
    local size="$3"
    local reason="$4"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S %Z')
    local user=$(whoami)
    
    echo "[$timestamp] [$user] $op | target: $target | size: $size | reason: $reason" >> "$LOG_FILE"
}

# Wrapper commands for common operations
safe-rm() {
    local target="$1"
    local reason="${2:-manual deletion}"
    local size=$(du -sh "$target" 2>/dev/null | cut -f1 || echo "unknown")
    log_op "DELETE" "$target" "$size" "$reason"
    rm -rf "$target"
    echo "Deleted: $target ($size) — logged"
}

safe-rm-dir() {
    local target="$1"
    local reason="${2:-manual directory removal}"
    local size=$(du -sh "$target" 2>/dev/null | cut -f1 || echo "unknown")
    log_op "RMDIR" "$target" "$size" "$reason"
    rm -rf "$target"
    echo "Removed directory: $target ($size) — logged"
}

log-apt-clean() {
    local before=$(df -h / | awk 'NR==2 {print $3}')
    log_op "APT_CLEAN" "cache+packages" "-$before" "cleanup"
    apt autoclean && apt autoremove -y
    local after=$(df -h / | awk 'NR==2 {print $3}')
    log_op "APT_CLEAN_DONE" "cache+packages" "before:$before after:$after" "cleanup completed"
}

log-docker-prune() {
    log_op "DOCKER_PRUNE" "images/containers" "unknown" "cleanup"
    docker system prune -af
    log_op "DOCKER_PRUNE_DONE" "images/containers" "done" "cleanup completed"
}

# Show recent operations
show-ops() {
    local n="${1:-20}"
    echo "=== Last $n file operations ==="
    tail -n "$n" "$LOG_FILE" 2>/dev/null || echo "No operations logged yet"
}

# Show operations by type
show-ops-by-type() {
    local op="$1"
    grep "\[$op\]" "$LOG_FILE" 2>/dev/null | tail -20
}

# Export to markdown report
export-ops-report() {
    local outfile="$LOG_DIR/file-operations-report-$(date +%Y-%m-%d).md"
    cat > "$outfile" << EOF
# File Operations Report

**Generated:** $(date '+%Y-%m-%d %H:%M:%S %Z')
**Log file:** $LOG_FILE

## Summary

| Operation Type | Count |
|---------------|-------|
| DELETE | $(grep -c "DELETE" "$LOG_FILE" 2>/dev/null || echo 0) |
| RMDIR | $(grep -c "RMDIR" "$LOG_FILE" 2>/dev/null || echo 0) |
| APT_CLEAN | $(grep -c "APT_CLEAN" "$LOG_FILE" 2>/dev/null || echo 0) |
| DOCKER_PRUNE | $(grep -c "DOCKER_PRUNE" "$LOG_FILE" 2>/dev/null || echo 0) |

## Recent Operations

\`\`\`
$(tail -30 "$LOG_FILE" 2>/dev/null)
\`\`\`

EOF
    echo "Report exported to: $outfile"
}

# If sourced, make functions available
if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
    echo "File operations logging loaded. Available commands:"
    echo "  safe-rm <path> [reason]        — Delete file/dir with logging"
    echo "  safe-rm-dir <path> [reason]    — Remove directory with logging"
    echo "  log-apt-clean                  — Run apt cleanup with logging"
    echo "  log-docker-prune               — Run docker prune with logging"
    echo "  show-ops [n]                   — Show last n operations (default 20)"
    echo "  show-ops-by-type <TYPE>        — Show operations by type"
    echo "  export-ops-report              — Generate markdown report"
    echo ""
    echo "Log file: $LOG_FILE"
    return 0
fi

# If run directly, show usage
echo "Source this script to use logging functions:"
echo "  source $0"
