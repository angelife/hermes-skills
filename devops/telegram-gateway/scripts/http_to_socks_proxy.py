"""
http_to_socks_proxy.py — HTTP proxy → SOCKS5 bridge.

Listens on 127.0.0.1:10809, accepts HTTP CONNECT, forwards to
SOCKS5 at 127.0.0.1:10808. SOCKS5 failures are translated to
HTTP 502 responses so httpx releases the connection immediately
(instead of the connection object lingering in the pool).

Designed for the Telegram gateway's send_path_degraded issue:
SOCKS5 RST/timeout gets swallowed at socket level → httpcore sees
no reclaim → pool fills → _send_path_degraded locks. HTTP proxy
makes failure visible as a non-200 response → httpx releases.

Usage:
    python3 http_to_socks_proxy.py
    # Proxy listening on 127.0.0.1:10809

    # Configure gateway to use HTTP proxy:
    # export HERMES_TELEGRAM_HTTP_PROXY=http://127.0.0.1:10809
    # Or in launchd plist:
    #   <key>HERMES_TELEGRAM_HTTP_PROXY</key>
    #   <string>http://127.0.0.1:10809</string>
"""
import asyncio
import logging
import struct

SOCKS5_HOST = "127.0.0.1"
SOCKS5_PORT = 10808
LISTEN_HOST = "127.0.0.1"
LISTEN_PORT = 10809

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("http2socks")


async def socks5_connect(host: str, port: int):
    """Connect to SOCKS5 proxy. Returns (reader, writer) or None."""
    try:
        r, w = await asyncio.wait_for(
            asyncio.open_connection(SOCKS5_HOST, SOCKS5_PORT),
            timeout=10,
        )
    except (OSError, asyncio.TimeoutError) as e:
        log.warning("SOCKS5 connect failed: %s", e)
        return None

    # SOCKS5 handshake: no auth
    w.write(struct.pack("!BBB", 5, 1, 0))
    await w.drain()
    resp = await asyncio.wait_for(r.readexactly(2), timeout=10)
    if resp[1] != 0:
        w.close()
        return None

    # CONNECT request
    host_bytes = host.encode() if isinstance(host, str) else host
    if isinstance(host, str):
        atyp = 3  # domain
        addr = struct.pack("!B", len(host_bytes)) + host_bytes
    else:
        atyp = 1  # IPv4
        addr = host_bytes

    req = struct.pack("!BBB", 5, 1, 0) + struct.pack("!B", atyp) + addr + struct.pack("!H", port)
    w.write(req)
    await w.drain()

    resp = await asyncio.wait_for(r.readexactly(4), timeout=10)
    if resp[1] != 0:
        log.warning("SOCKS5 CONNECT refused (code %d) to %s:%s", resp[1], host, port)
        w.close()
        return None

    # skip remaining reply (bnd.addr + bnd.port)
    if resp[3] == 1:
        await r.readexactly(6)
    elif resp[3] == 3:
        alen = (await r.readexactly(1))[0]
        await r.readexactly(alen + 2)
    elif resp[3] == 4:
        await r.readexactly(18)

    return r, w


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """Handle one HTTP CONNECT request."""
    try:
        data = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=15)
    except (asyncio.IncompleteReadError, asyncio.TimeoutError):
        writer.close()
        return

    request_line = data.split(b"\r\n")[0].decode("utf-8", errors="replace")
    parts = request_line.split()

    if len(parts) < 3 or parts[0] != "CONNECT":
        writer.write(b"HTTP/1.1 405 Method Not Allowed\r\n\r\n")
        await writer.drain()
        writer.close()
        return

    host_port = parts[1]
    host, _, port_str = host_port.partition(":")
    try:
        port = int(port_str)
    except ValueError:
        writer.write(b"HTTP/1.1 400 Bad Request\r\n\r\n")
        await writer.drain()
        writer.close()
        return

    # Connect via SOCKS5
    result = await socks5_connect(host, port)
    if result is None:
        # SOCKS5 failed => return HTTP 502 => httpx sees non-200 => releases connection
        writer.write(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
        await writer.drain()
        writer.close()
        return

    remote_r, remote_w = result
    writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
    await writer.drain()

    async def pipe(src, dst):
        try:
            while True:
                data = await asyncio.wait_for(src.read(65536), timeout=300)
                if not data:
                    break
                dst.write(data)
                await dst.drain()
        except (OSError, asyncio.TimeoutError, asyncio.IncompleteReadError):
            pass

    try:
        await asyncio.gather(
            pipe(reader, remote_w),
            pipe(remote_r, writer),
        )
    finally:
        remote_w.close()
        writer.close()


async def main():
    server = await asyncio.start_server(handle_client, LISTEN_HOST, LISTEN_PORT)
    log.info("HTTP->SOCKS5 proxy on %s:%s -> %s:%s", LISTEN_HOST, LISTEN_PORT, SOCKS5_HOST, SOCKS5_PORT)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
