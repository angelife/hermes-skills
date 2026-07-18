#!/usr/bin/env python3
"""
Hermes browser login — one-time bootstrap for persistent browser profiles.

Usage:
    python3 <skill_path>/scripts/browser-login.py gemini    # Login to Gemini
    python3 <skill_path>/scripts/browser-login.py status    # Check all profiles

Opens a Playwright persistent-context browser for the given service,
waits for the user to log in manually, verifies the session is active,
then writes a .ready status file so LoginAwareProvider uses Playwright.

Status file: ~/.hermes/browser-profiles/<service>/<service>.ready
"""

import json, os, subprocess, sys, time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PARENT_DIR = SCRIPT_DIR.parent
PROFILE_BASE = Path.home() / ".hermes" / "browser-profiles"
PLAYWRIGHT_JS = PARENT_DIR / "scripts" / "playwright-browser.js"

SERVICES = {
    "gemini": {
        "name": "Google Gemini",
        "url": "https://gemini.google.com/app",
        "status_file": "gemini.ready",
    },
}

def launch_and_wait(service: str, timeout: int = 300) -> bool:
    info = SERVICES[service]
    profile_dir = PROFILE_BASE / service
    status_file = profile_dir / info["status_file"]

    print(f"\n{'='*60}")
    print(f"  Opening browser for {info['name']} login")
    print(f"  Log in manually in the browser window")
    print(f"  Timeout: {timeout}s")
    print(f"{'='*60}\n")

    env = {**os.environ, "PW_PROFILE_DIR": str(profile_dir)}

    # Navigate to login page
    r = subprocess.run(["node", str(PLAYWRIGHT_JS), "navigate", info["url"], "30"],
                       capture_output=True, text=True, timeout=60, cwd=str(SCRIPT_DIR), env=env)
    data = json.loads(r.stdout) if r.stdout.strip() else {"ok": False}
    if not data.get("ok"):
        print(f"  Browser launch failed: {data.get('error', '?')}")
        return False

    # Poll for login completion
    start = time.time()
    last_msg = 0
    while time.time() - start < timeout:
        elapsed = int(time.time() - start)
        if elapsed - last_msg > 15:
            print(f"  [{elapsed}s] Waiting for login...")
            last_msg = elapsed

        r2 = subprocess.run(["node", str(PLAYWRIGHT_JS), "state", info["url"], "10"],
                            capture_output=True, text=True, timeout=20,
                            cwd=str(SCRIPT_DIR), env=env)
        try:
            s = json.loads(r2.stdout)
            if s.get("ok") and info["url"] in s.get("url", "") and "Sign in" not in s.get("title", ""):
                profile_dir.mkdir(parents=True, exist_ok=True)
                status_file.write_text(json.dumps({"ready": True, "at": time.time()}))
                print(f"\n  Login confirmed. Profile saved.")
                return True
        except: pass
        time.sleep(5)

    print(f"\n  Timeout after {timeout}s")
    return False

def show_status():
    print(f"\nBrowser Profile Status:")
    print(f"{'='*40}")
    for svc, info in SERVICES.items():
        sf = PROFILE_BASE / svc / info["status_file"]
        ready = sf.exists()
        print(f"  {info['name']:15s}  {'READY' if ready else 'not set up'}")

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "status":
        show_status()
    elif sys.argv[1] in SERVICES:
        launch_and_wait(sys.argv[1])
    else:
        print(f"Service must be one of: {list(SERVICES.keys())}")