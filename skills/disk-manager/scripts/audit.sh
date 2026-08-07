#!/bin/bash
# audit.sh — Comprehensive VPS disk usage audit
# Usage: sudo bash audit.sh [output-dir]

OUTPUT_DIR="${1:-/home/cloudy/.openclaw/workspace/reference}"
HOST=$(hostname)
DATE=$(date '+%Y-%m-%d')
REPORT="$OUTPUT_DIR/vps-disk-usage-$DATE.md"

mkdir -p "$OUTPUT_DIR"

cat > "$REPORT" << EOF
# VPS Disk Usage Audit Report

**Date:** $DATE
**Host:** $HOST
**Auditor:** Cloudy

---

## Executive Summary

| Metric | Value |
|--------|-------|
| **Total Disk** | $(df -h / | awk 'NR==2 {print $2}') |
| **Used** | $(df -h / | awk 'NR==2 {print $3}') ($(df -h / | awk 'NR==2 {gsub(/%/,""); print $5}')%) |
| **Available** | $(df -h / | awk 'NR==2 {print $4}') |
| **Inode Usage** | $(df -i / | awk 'NR==2 {print $5}') ($(df -i / | awk 'NR==2 {print $3}') / $(df -i / | awk 'NR==2 {print $2}')) |

### Top 5 Disk Consumers

EOF

echo "### Root Filesystem Breakdown" >> "$REPORT"
echo "" >> "$REPORT"
echo "| Directory | Size |" >> "$REPORT"
echo "|-----------|------|" >> "$REPORT"
du -sh /* 2>/dev/null | sort -rh | head -10 | while read size dir; do
    echo "| $dir | $size |" >> "$REPORT"
done

echo "" >> "$REPORT"
echo "### Home Directory Breakdown" >> "$REPORT"
echo "" >> "$REPORT"
echo "| User | Size |" >> "$REPORT"
echo "|------|------|" >> "$REPORT"
du -sh /home/* 2>/dev/null | sort -rh | head -10 | while read size dir; do
    echo "| $dir | $size |" >> "$REPORT"
done

echo "" >> "$REPORT"
echo "### Large Files (>50MB)" >> "$REPORT"
echo "" >> "$REPORT"
echo "| Path | Size |" >> "$REPORT"
echo "|------|------|" >> "$REPORT"
find /home -type f -size +50M 2>/dev/null | head -20 | while read f; do
    ls -lh "$f" 2>/dev/null | awk '{print "| " $9 " | " $5 " |"}' >> "$REPORT"
done

echo "" >> "$REPORT"
echo "### Snap Packages" >> "$REPORT"
echo "" >> "$REPORT"
echo "\`\`\`" >> "$REPORT"
snap list 2>/dev/null || echo "snap not installed" >> "$REPORT"
echo "\`\`\`" >> "$REPORT"

echo "" >> "$REPORT"
echo "### Docker Images" >> "$REPORT"
echo "" >> "$REPORT"
echo "\`\`\`" >> "$REPORT"
docker images --format "table {{.Repository}}\t{{.Size}}" 2>/dev/null | head -10 || echo "docker not available" >> "$REPORT"
echo "\`\`\`" >> "$REPORT"

echo "" >> "$REPORT"
echo "## Recommendations" >> "$REPORT"
echo "" >> "$REPORT"
echo "1. Run \`apt autoclean && apt autoremove\`" >> "$REPORT"
echo "2. Clean npm cache: \`npm cache clean --force\`" >> "$REPORT"
echo "3. Check for old Playwright Chromium versions in \`~/.cache/ms-playwright/\`" >> "$REPORT"
echo "4. Review Docker images: \`docker image prune -a\`" >> "$REPORT"
echo "5. Compress old session files: \`find ~/.openclaw/agents/main/sessions -name '*.jsonl' -mtime +30 -exec gzip {} +\`" >> "$REPORT"

echo "Report saved to: $REPORT"
