#!/usr/bin/env python3
"""
ADB HTTP CONNECT Proxy — tunnel phone internet through Mac via adb reverse.

Usage:
  1. python3 adb-http-connect-proxy.py [port]   # default 8080
  2. adb reverse tcp:<port> tcp:<port>
  3. adb shell settings put global http_proxy localhost:<port>
  4. Verify: adb shell curl -s -o /dev/null -w '%{http_code}' http://example.com

Supports both HTTP (forward proxy) and HTTPS (CONNECT tunnel).
"""
import socket
import sys
import threading
from urllib.parse import urlparse


def forward(src, dst):
    """Bidirectional copy between two sockets."""
    try:
        while True:
            data = src.recv(65536)
            if not data:
                break
            dst.sendall(data)
    except (BrokenPipeError, ConnectionResetError, OSError):
        pass
    finally:
        for s in (src, dst):
            try:
                s.close()
            except OSError:
                pass


def handle_connect(client, target_bytes):
    """Handle HTTPS CONNECT tunnel."""
    host, port_str = target_bytes.rsplit(b":", 1)
    port = int(port_str)
    host = host.decode()
    try:
        remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote.settimeout(30)
        remote.connect((host, port))
        client.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        t1 = threading.Thread(target=forward, args=(client, remote), daemon=True)
        t2 = threading.Thread(target=forward, args=(remote, client), daemon=True)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
    except Exception as e:
        try:
            client.sendall(f"HTTP/1.1 502 Bad Gateway\r\n\r\n{str(e)}".encode())
        except OSError:
            pass
        client.close()


def handle_http(client, raw_request):
    """Handle plain HTTP forward."""
    first_line = raw_request.split(b"\r\n")[0]
    parts = first_line.split(b" ")
    if len(parts) < 2:
        client.close()
        return
    target = parts[1].decode()
    parsed = urlparse(target)
    host = parsed.hostname
    port = parsed.port or 80
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query

    try:
        remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote.settimeout(30)
        remote.connect((host, port))
        # Rewrite absolute URL → relative path
        new_req = raw_request.replace(parts[1], path.encode(), 1)
        remote.sendall(new_req)
        forward(remote, client)
    except Exception as e:
        try:
            client.sendall(f"HTTP/1.1 502 Bad Gateway\r\n\r\n{str(e)}".encode())
        except OSError:
            pass
        client.close()


def handle(client):
    try:
        data = client.recv(65536)
        if not data:
            client.close()
            return
        method = data.split(b" ", 1)[0]
        if method == b"CONNECT":
            target = data.split(b" ", 2)[1]
            handle_connect(client, target)
        else:
            handle_http(client, data)
    except Exception:
        pass
    finally:
        try:
            client.close()
        except OSError:
            pass


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", port))
    server.listen(100)
    print(f"ADB HTTP CONNECT proxy → 127.0.0.1:{port}", flush=True)
    while True:
        client, addr = server.accept()
        threading.Thread(target=handle, args=(client,), daemon=True).start()


if __name__ == "__main__":
    main()
