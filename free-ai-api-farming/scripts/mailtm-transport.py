#!/usr/bin/env python3
"""mailtm_transport.py — Free temp mail backend using mail.tm (no API key needed).
Place in xconsole_client/ of grok-build-auth to add -e mailtm option.

Usage in run.py:
  elif backend == "mailtm":
      from xconsole_client.mailtm_transport import MailTmInbox
      inbox = MailTmInbox(prefix="xai")
      email = inbox.create()
      return email, inbox
"""

from __future__ import annotations
import re, time, requests
from typing import Optional

BASE_URL = "https://api.mail.tm"


class MailTmInbox:
    """mail.tm inbox - completely free, no API key required.
    Works from China (unlike tempmail.lol free tier which blocks CN IPs).
    """

    def __init__(self, api_key: str = "", prefix: str = "xai", debug: bool = False):
        self.prefix = prefix
        self.debug = debug
        self.address = ""
        self.token = ""
        self._created = False

    def create(self) -> str:
        suffix = int(time.time() * 1000) % 100000
        addr = f"{self.prefix}{suffix}@web-library.net"
        pw = "XaiTest99!!"

        r = requests.post(f"{BASE_URL}/accounts", json={
            "address": addr, "password": pw
        }, timeout=15)
        if r.status_code not in (200, 201):
            raise RuntimeError(f"mail.tm create failed: {r.status_code} {r.text[:200]}")

        r2 = requests.post(f"{BASE_URL}/token", json={
            "address": addr, "password": pw
        }, timeout=15)
        if r2.status_code != 200:
            raise RuntimeError(f"mail.tm login failed: {r2.status_code}")

        data = r2.json()
        self.address = addr
        self.token = data["token"]
        self._created = True
        if self.debug:
            print(f"  [Mail.tm] inbox: {addr}")
        return addr

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"}

    def get_emails(self) -> list[dict]:
        if not self._created:
            return []
        r = requests.get(f"{BASE_URL}/messages",
                         headers=self._headers(), timeout=15)
        if r.status_code != 200:
            return []
        data = r.json()
        return data.get("hydra:member", [])

    def wait_for_code(self, timeout: Optional[float] = 90.0) -> str:
        deadline = time.time() + (timeout or 90)
        while time.time() < deadline:
            emails = self.get_emails()
            for email in emails:
                msg_id = email.get("id", "")
                if msg_id:
                    r = requests.get(f"{BASE_URL}/messages/{msg_id}",
                                     headers=self._headers(), timeout=15)
                    if r.status_code == 200:
                        body = r.json().get("html", "") or r.json().get("text", "")
                        m = re.search(r'([A-Z0-9]{6})', body)
                        if m:
                            code = m.group(1)
                            requests.delete(f"{BASE_URL}/messages/{msg_id}",
                                            headers=self._headers(), timeout=10)
                            return code
            time.sleep(3)
        raise TimeoutError("No verification code received within timeout")
