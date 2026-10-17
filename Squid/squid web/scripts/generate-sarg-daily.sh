#!/usr/bin/env bash
# ==============================================================================
# Innspark Solutions - SARG Automated Daily Report Generation Script
# Location on Server 2: /usr/local/bin/generate-sarg-daily.sh
# ==============================================================================

set -e

LOG_FILE="/var/log/squid/access.log"
REPORT_DIR="/var/www/html/sarg"
SARG_BIN="/usr/bin/sarg"
TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")

echo "[$TIMESTAMP] Starting daily SARG report generation..."

# 1. Check if SARG binary exists
if [ ! -x "$SARG_BIN" ]; then
    echo "[$TIMESTAMP] Error: SARG executable not found at $SARG_BIN" >&2
    exit 1
fi

# 2. Check if Squid log exists and is readable
if [ ! -f "$LOG_FILE" ]; then
    echo "[$TIMESTAMP] Warning: Squid log $LOG_FILE does not exist. Creating empty log."
    touch "$LOG_FILE"
    chown proxy:proxy "$LOG_FILE"
fi

# 3. Ensure report directory exists with correct ownership
mkdir -p "$REPORT_DIR"
chown -R www-data:www-data "$REPORT_DIR"

# 4. Execute SARG with today's date range
TODAY=$(date +%d/%m/%Y)
$SARG_BIN -d "$TODAY-$TODAY" > /dev/null 2>&1 || $SARG_BIN > /dev/null 2>&1

# 5. Fix permissions after generation so web server can read HTML
chown -R www-data:www-data "$REPORT_DIR"
chmod -R 755 "$REPORT_DIR"

echo "[$TIMESTAMP] SARG daily report generation completed successfully."
