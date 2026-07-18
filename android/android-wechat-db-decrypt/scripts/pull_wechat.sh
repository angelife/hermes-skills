#!/bin/bash
# Auto-pull and decrypt WeChat data
# Called by cron - script goes in ~/.hermes/scripts/
# See references/automated-pull-workflow.md for usage

DB_PATH="/data/data/com.tencent.mm/MicroMsg/d65f989d7e35cd4b56910fb8d96d4ec5/EnMicroMsg.db"
ADB_TCP="192.168.1.26:5555"
ADB_USB="a6520fa3"
KEY="0273023"
OUTPUT_DIR="$HOME/.hermes/cron/output"
SQLCIPHER="/tmp/sqlcipher/sqlite3"

mkdir -p "$OUTPUT_DIR"

# Determine which ADB target to use (USB preferred, TCP fallback)
ADB_TARGET=""
if adb devices 2>/dev/null | grep -q "$ADB_USB"; then
    ADB_TARGET="$ADB_USB"
elif adb connect "$ADB_TCP" 2>/dev/null | grep -q "connected"; then
    ADB_TARGET="$ADB_TCP"
    sleep 1
else
    echo "$(date) ADB device not available (USB or TCP)" >> "$OUTPUT_DIR/wechat_cron.log"
    exit 1
fi

# Pull encrypted DB via exec-out for speed
adb -s "$ADB_TARGET" exec-out "su -c 'cat $DB_PATH'" > /tmp/EnMicroMsg_cron_encrypted.db 2>/dev/null
ENC_SIZE=$(stat -f%z /tmp/EnMicroMsg_cron_encrypted.db 2>/dev/null)

if [ -z "$ENC_SIZE" ] || [ "$ENC_SIZE" -lt 1000000 ]; then
    echo "DB pull failed (size=$ENC_SIZE) at $(date)" >> "$OUTPUT_DIR/wechat_cron.log"
    exit 1
fi

# Decrypt (direct PRAGMA query, not ATTACH+export which can fail with 'malformed')
$SQLCIPHER /tmp/EnMicroMsg_cron_encrypted.db <<'EOF' 2>/dev/null
PRAGMA key = '0273023';
PRAGMA cipher_compatibility = 1;
ATTACH DATABASE '/tmp/EnMicroMsg_cron_decrypted.db' AS decrypted KEY '';
SELECT sqlcipher_export('decrypted');
DETACH DATABASE decrypted;
EOF

# Compare with previous message count to detect new messages
PREV_COUNT=$(cat "$OUTPUT_DIR/wechat_msg_count.txt" 2>/dev/null || echo 0)
CUR_COUNT=$($SQLCIPHER /tmp/EnMicroMsg_cron_decrypted.db "SELECT COUNT(*) FROM message;" 2>/dev/null)
echo "$CUR_COUNT" > "$OUTPUT_DIR/wechat_msg_count.txt"

NEW_MSG=$((CUR_COUNT - PREV_COUNT))
if [ "$NEW_MSG" -gt 0 ] && [ "$PREV_COUNT" -gt 0 ]; then
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$TIMESTAMP] +$NEW_MSG new messages (total: $CUR_COUNT)" >> "$OUTPUT_DIR/wechat_cron.log"
fi

# Copy to latest for analysis
cp /tmp/EnMicroMsg_cron_decrypted.db /tmp/EnMicroMsg_decrypted_latest.db 2>/dev/null

echo "OK: total=$CUR_COUNT new=$NEW_MSG"