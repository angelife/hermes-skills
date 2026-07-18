#!/usr/bin/env python3
"""Watchdog for Hermes Telegram gateway pool timeout.

Detects 3+ Pool timeout errors in last 10 minutes of gateway.log
and restarts the gateway via launchctl if threshold exceeded.

Install as cron: */5 * * * * python3 /Users/macos/.hermes/scripts/gateway-watchdog.py
"""

import os
import subprocess
import time
from collections import deque

LOG_FILE = os.path.expanduser("~/.hermes/logs/gateway.log")
PLIST = os.path.expanduser("~/Library/LaunchAgents/ai.hermes.gateway.plist")
THRESHOLD = 3
WINDOW_SECONDS = 600  # 10 minutes


def count_recent_pool_timeouts():
    if not os.path.exists(LOG_FILE):
        return 0
    now = time.time()
    count = 0
    with open(LOG_FILE, "r") as f:
        for line in f:
            if "Pool timeout" in line:
                # Parse timestamp from log line
                try:
                    ts_str = line[:19]
                    ts = time.mktime(time.strptime(ts_str, "%Y-%m-%d %H:%M:%S"))
                    if now - ts < WINDOW_SECONDS:
                        count += 1
                except (ValueError, IndexError):
                    continue
    return count


def restart_gateway():
    subprocess.run(["launchctl", "unload", PLIST], capture_output=True)
    time.sleep(3)
    subprocess.run(["launchctl", "load", PLIST], capture_output=True)


if __name__ == "__main__":
    count = count_recent_pool_timeouts()
    if count >= THRESHOLD:
        restart_gateway()
        print(f"[watchdog] {count} pool timeouts detected, gateway restarted")
    else:
        print(f"[watchdog] OK - {count} pool timeouts in last 10min")
