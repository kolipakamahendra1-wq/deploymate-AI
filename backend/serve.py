"""Production entry point: serve the API on one dual-stack (IPv4 + IPv6) socket.

`uvicorn --host ::` produces an IPv6-only socket (asyncio sets IPV6_V6ONLY), which
breaks IPv4 health checks; `--host 0.0.0.0` breaks IPv6-only private networks.
One socket with IPV6_V6ONLY off accepts both.
"""
from __future__ import annotations

import os
import socket

import uvicorn


def main() -> None:
    sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
    sock.bind(("::", int(os.environ.get("PORT", "8000"))))
    config = uvicorn.Config("backend.api.main:app", proxy_headers=True, forwarded_allow_ips="*")
    uvicorn.Server(config).run(sockets=[sock])


if __name__ == "__main__":
    main()
