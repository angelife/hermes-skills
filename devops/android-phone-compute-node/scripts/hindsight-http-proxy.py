#!/usr/bin/env python3
"""
Zero-dependency HTTP reverse proxy for Android phones.

Routes all HTTP(S) traffic from phone-bound clients to an upstream server.
No pip install needed — uses only Python stdlib (http.server, urllib.request).

Common use case: Phone is the LAN gateway for other bots/services, but the
upstream server (e.g. Hindsight memory server) runs on a different machine.
Deploy this proxy on the phone, point bots to http://phone-ip:8090, and
only the phone's UPSTREAM config needs changing when the host IP changes.

Usage:
  1. Edit UPSTREAM to point to the real server URL
  2. Push to phone: adb push hindsight-http-proxy.py /data/local/tmp/
  3. Run:
       adb shell "su -c '
         nohup python3 /data/local/tmp/hindsight-http-proxy.py > /data/local/tmp/proxy.log 2>&1 &
       '"
  4. Verify: curl http://phone-ip:8090/health

  Magisk auto-start: copy to /data/adb/service.d/ as a wrapper script.
"""

import http.server
import urllib.request
import urllib.error
import json
import sys

UPSTREAM = "http://192.168.1.8:8888"   # ← CHANGE THIS to your upstream URL
LISTEN = ("0.0.0.0", 8090)
TIMEOUT = 30


class Proxy(http.server.BaseHTTPRequestHandler):
    def _forward(self):
        url = UPSTREAM + self.path
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0)) or None
        hdrs = {k: v for k, v in self.headers.items()
                if k.lower() not in ("host", "content-length")}
        req = urllib.request.Request(url, data=body, method=self.command, headers=hdrs)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                self.send_response(r.status)
                for k, v in r.headers.items():
                    if k.lower() not in ("transfer-encoding", "connection"):
                        self.send_header(k, v)
                self.end_headers()
                self.wfile.write(r.read())
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            self.send_response(502)
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    do_GET = do_POST = do_PUT = do_DELETE = do_PATCH = _forward


if __name__ == "__main__":
    srv = http.server.ThreadingHTTPServer(LISTEN, Proxy)
    print(f"Hindsight proxy on {LISTEN[0]}:{LISTEN[1]} -> {UPSTREAM}", flush=True)
    srv.serve_forever()
