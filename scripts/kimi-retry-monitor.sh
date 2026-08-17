#!/bin/bash
# OpenClaw Kimi Retry Storm Monitor (v2 — gateway log tail)
# Detects retry storms by parsing gateway logs, not lsof
#
# Usage:
#   ./kimi-retry-monitor.sh start    # Start daemon
#   ./kimi-retry-monitor.sh stop     # Stop daemon
#   ./kimi-retry-monitor.sh status   # Check status
#   ./kimi-retry-monitor.sh run      # Run in foreground (debug)
#   ./kimi-retry-monitor.sh check [MINUTES]  # Query logs

set -euo pipefail

LOGDIR="${HOME}/.openclaw/logs/kimi-monitor"
GATEWAY_LOG="${HOME}/Library/Logs/openclaw/gateway.log"
PIDFILE="${LOGDIR}/monitor.pid"

# Thresholds
POLL_INTERVAL=2           # seconds between status snapshots
BURST_THRESHOLD=3         # in-flight requests to trigger burst alert
RAPID_WINDOW_SEC=10       # window for rapid-fire detection
RAPID_COUNT=4             # requests in window to count as rapid-fire
LOG_KEEP_HOURS=24

mkdir -p "$LOGDIR"

get_logfile() {
    echo "${LOGDIR}/$(date +%Y%m%d_%H).log"
}

log() {
    local level="$1"; shift
    local ts; ts="$(date '+%Y-%m-%dT%H:%M:%S%z')"
    echo "${ts} [${level}] $*" >> "$(get_logfile)"
}

# ── Core monitor: tail gateway log and parse ─────────────────────────

monitor_loop() {
    local current_log="$(get_logfile)"
    log "info" "Monitor started. PID=$$. Tailing $GATEWAY_LOG"
    log "info" "Thresholds: burst=${BURST_THRESHOLD} in-flight, rapid=${RAPID_COUNT} in ${RAPID_WINDOW_SEC}s"

    if [ ! -r "$GATEWAY_LOG" ]; then
        log "error" "Cannot read gateway log: $GATEWAY_LOG"
        exit 1
    fi

    # State tracking
    local in_flight=0
    local -a recent_starts=()  # array of epoch timestamps
    local last_logfile="$current_log"

    # Tail -F follows log rotation, -n 0 starts from current end
    tail -n 0 -F "$GATEWAY_LOG" 2>/dev/null | while IFS= read -r line; do

        # Rotate our own log hourly
        current_log="$(get_logfile)"
        if [ "$current_log" != "$last_logfile" ]; then
            last_logfile="$current_log"
        fi

        # --- Parse gateway log lines ---

        # Detect Kimi request START
        if echo "$line" | grep -qE '\[provider-transport-fetch\].*start provider=kimi'; then
            in_flight=$((in_flight + 1))
            local now; now="$(date +%s)"
            recent_starts+=("$now")

            # Extract model from line
            local model
            model="$(echo "$line" | grep -oE 'model=[^ ]+' | cut -d= -f2 || echo '?')"
            log "start" "model=$model in_flight=$in_flight"

            # Burst: in-flight threshold
            if [ "$in_flight" -ge "$BURST_THRESHOLD" ]; then
                log "BURST" "In-flight requests: $in_flight (threshold=$BURST_THRESHOLD)"
            fi

            # Burst: rapid-fire (many starts in short window)
            # Clean old entries outside window
            local cutoff=$((now - RAPID_WINDOW_SEC))
            local -a fresh_starts=()
            for t in "${recent_starts[@]}"; do
                [ "$t" -ge "$cutoff" ] && fresh_starts+=("$t")
            done
            recent_starts=("${fresh_starts[@]}")

            if [ ${#recent_starts[@]} -ge "$RAPID_COUNT" ]; then
                log "BURST" "Rapid-fire: ${#recent_starts[@]} Kimi starts in ${RAPID_WINDOW_SEC}s"
                recent_starts=()  # reset to avoid spam
            fi
        fi

        # Detect Kimi RESPONSE
        if echo "$line" | grep -qE '\[provider-transport-fetch\].*response provider=kimi'; then
            in_flight=$((in_flight - 1))
            [ "$in_flight" -lt 0 ] && in_flight=0

            local model status elapsed
            model="$(echo "$line" | grep -oE 'model=[^ ]+' | cut -d= -f2 || echo '?')"
            status="$(echo "$line" | grep -oE 'status=[0-9]+' | cut -d= -f2 || echo '?')"
            elapsed="$(echo "$line" | grep -oE 'elapsedMs=[0-9]+' | cut -d= -f2 || echo '?')"

            log "response" "model=$model status=$status elapsed=${elapsed}ms in_flight=$in_flight"

            # Alert on rate-limit
            if [ "$status" = "429" ]; then
                log "ALERT" "HTTP 429 (rate-limited) from Kimi API — model=$model"
            fi
            if echo "$line" | grep -qiE 'rate.limit|rate-limit|temporarily.rate-limited|insufficient_quota'; then
                log "ALERT" "Rate-limit keyword in response — model=$model"
            fi
        fi

        # Periodic cleanup: purge old monitor logs every ~1000 lines
        # (lightweight — just touches find every ~30 min of log activity)
        if [ $((RANDOM % 1000)) -eq 0 ]; then
            find "$LOGDIR" -name "*.log" -type f -mmin +$((LOG_KEEP_HOURS * 60)) -delete 2>/dev/null || true
        fi
    done
}

# ── CLI commands ─────────────────────────────────────────────────────

cmd_start() {
    if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
        echo "Monitor already running (PID $(cat "$PIDFILE"))"
        return 0
    fi
    # macOS: no setsid, use subshell + disown
    (
        bash "$0" run > /dev/null 2>&1 &
        echo $! > "$PIDFILE"
        disown
    )
    sleep 1
    if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
        echo "Started kimi-retry-monitor (PID $(cat "$PIDFILE"))"
        echo "Logs: $LOGDIR/"
    else
        echo "Failed to start monitor — check $LOGDIR/ for errors"
        rm -f "$PIDFILE"
        return 1
    fi
}

cmd_stop() {
    if [ ! -f "$PIDFILE" ]; then
        echo "Monitor not running"; return 0
    fi
    local pid; pid="$(cat "$PIDFILE")"
    if kill -0 "$pid" 2>/dev/null; then
        kill "$pid" 2>/dev/null || true
        # Also kill the tail subprocess (child of our shell)
        pkill -P "$pid" 2>/dev/null || true
    fi
    rm -f "$PIDFILE"
    echo "Stopped monitor"
}

cmd_status() {
    if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
        echo "Monitor running (PID $(cat "$PIDFILE"))"
        local latest; latest="$(ls -t "$LOGDIR"/*.log 2>/dev/null | head -1)"
        [ -n "$latest" ] && echo "Latest log: $latest" && echo "" && tail -15 "$latest"
    else
        echo "Monitor not running"
        rm -f "$PIDFILE"
    fi
}

cmd_check() {
    local minutes="${1:-10}"
    echo "=== Kimi Retry Monitor Report (last ${minutes} minutes) ==="
    echo "Generated: $(date '+%Y-%m-%d %H:%M:%S %Z')"
    echo ""

    # Find relevant log files
    local logs=()
    local current_log; current_log="$(get_logfile)"
    [ -f "$current_log" ] && logs+=("$current_log")
    local prev_log; prev_log="${LOGDIR}/$(date -v-1H +%Y%m%d_%H 2>/dev/null || echo '').log"
    [ -f "$prev_log" ] && [ "$prev_log" != "$current_log" ] && logs+=("$prev_log")

    if [ ${#logs[@]} -eq 0 ]; then
        echo "No monitor logs found."
        exit 1
    fi

    # --- Section 1: Request activity ---
    echo "📊 Kimi Request Activity:"
    echo "-------------------------"
    local max_in_flight=0
    local burst_count=0
    for logf in "${logs[@]}"; do
        while IFS= read -r l; do
            if echo "$l" | grep -q '\[start\]'; then
                echo "$l"
            fi
            if echo "$l" | grep -q '\[BURST\]'; then
                echo "🔥 $l"
                burst_count=$((burst_count + 1))
            fi
            # Track max in-flight
            local ifc
            ifc="$(echo "$l" | grep -oE 'in_flight=[0-9]+' | cut -d= -f2 || echo 0)"
            [ "$ifc" -gt "$max_in_flight" ] && max_in_flight=$ifc
        done < <(grep -E '\[start\]|\[BURST\]' "$logf" 2>/dev/null | tail -50)
    done
    echo "Max in-flight observed: $max_in_flight"
    echo ""

    # --- Section 2: Rate-limit / 429 events ---
    echo "🚨 Rate-Limit / 429 Events:"
    echo "---------------------------"
    local alert_count=0
    for logf in "${logs[@]}"; do
        local alerts
        alerts="$(grep '\[ALERT\]' "$logf" 2>/dev/null | tail -20 || true)"
        if [ -n "$alerts" ]; then
            echo "$alerts"
            alert_count=$(($(echo "$alerts" | grep -c .) + alert_count))
        fi
    done
    if [ "$alert_count" -eq 0 ]; then
        echo "No rate-limit or 429 events in monitor logs."
    fi
    echo ""

    # --- Section 3: Also check raw gateway log for 429s ---
    echo "Gateway log (direct check):"
    echo "---------------------------"
    if [ -r "$GATEWAY_LOG" ]; then
        local gateway_429s
        gateway_429s="$(grep -E 'status=429.*provider=kimi|provider=kimi.*status=429' "$GATEWAY_LOG" 2>/dev/null | tail -10 || true)"
        if [ -n "$gateway_429s" ]; then
            echo "$gateway_429s"
        else
            echo "No Kimi 429s in gateway log."
        fi
    else
        echo "Gateway log not readable: $GATEWAY_LOG"
    fi
    echo ""

    # --- Section 4: Verdict ---
    echo "📝 Verdict:"
    echo "-----------"
    if [ "$burst_count" -gt 0 ] && [ "$alert_count" -gt 0 ]; then
        echo "⚠️  RETRY STORM LIKELY: Request bursts detected AND rate-limit/429 responses found."
        echo "   Suggests OpenClaw or harness was hammering the API."
    elif [ "$burst_count" -gt 0 ] && [ "$alert_count" -eq 0 ]; then
        echo "⚠️  BURSTS WITHOUT REJECTION: Rapid requests detected, but no 429s found."
        echo "   Could be normal load or server handled it."
    elif [ "$burst_count" -eq 0 ] && [ "$alert_count" -gt 0 ]; then
        echo "⚠️  RATE-LIMIT WITHOUT BURST: 429s returned despite normal request pace."
        echo "   Likely API-side throttling (quota, plan limits), not retry storm."
    else
        echo "✅ NO ISSUES: No bursts or rate-limit events in the monitored period."
        echo "   The error was not preceded by detectable retry activity."
    fi
}

# ── Entrypoint ───────────────────────────────────────────────────────

case "${1:-}" in
    start)  cmd_start ;;
    stop)   cmd_stop ;;
    status) cmd_status ;;
    run)    monitor_loop ;;
    check)  cmd_check "${2:-10}" ;;
    *)
        echo "OpenClaw Kimi Retry Storm Monitor"
        echo ""
        echo "Usage: $0 {start|stop|status|run|check [minutes]}"
        echo ""
        echo "  start          Start background monitor"
        echo "  stop           Stop monitor"
        echo "  status         Show status + recent log tail"
        echo "  run            Run in foreground (for LaunchAgent/debug)"
        echo "  check [N]      Analyze last N minutes (default: 10)"
        echo ""
        echo "Logs:    ${LOGDIR}/"
        echo "Config:  burst=${BURST_THRESHOLD} in-flight, rapid=${RAPID_COUNT} in ${RAPID_WINDOW_SEC}s"
        exit 1
        ;;
esac
