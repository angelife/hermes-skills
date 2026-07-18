# Termux on Android: Hermes Gateway Intercepts adb shell (Session 2026-06-26)

## Problem
All `adb shell` commands sent from Mac are intercepted by Hermes gateway running in Termux on Android (Mi8/坚果3). Cannot restart or start gateway from Mac.

## Root Cause
Hermes gateway is running in Termux and intercepts all `adb shell` stdin/stdout because it wraps the shell environment. Every `adb -s <device> shell "..."` command goes through Hermes' command pipeline and gets `SIGTERM`-propagated.

## Workaround Hierarchy
1. **Best**: User runs commands directly in Termux — `hermes gateway restart`
2. **Alternative**: Use `termux-wake-lock` to prevent kills while user keeps Termux open
3. **Fallback**: USB tethering + direct USB connection (bypasses Hermes if gateway not yet running)
4. **Never try**: `run-as com.termux` — same interception applies
5. **Never try**: `su -c` or `shizuku` — may not be available or functional on all devices

## Key Insight
This applies to ANY Android device where Hermes gateway is actively running. The gateway acts as a middleware shell. Commands from Mac → adb shell → Hermes → executed. Always check if gateway is running FIRST, and plan for local execution as the primary path.

## Prevention
When setting up Hermes on Android:
1. Document the `hermes gateway start/stop/restart` commands for the user
2. If you need to change config, push files first (`adb push`), then instruct user to restart
3. Never assume `adb shell` is reliable for state changes on Android
