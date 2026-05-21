#!/usr/bin/env python3.12
"""
Simple HTTP server to serve the streams directory.
Access the playlist at: http://YOUR_SERVER_IP:8080/bo.m3u
"""

import http.server
import socketserver
from pathlib import Path

PORT = 8080
SERVE_DIR = Path(__file__).parent / "streams"


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SERVE_DIR), **kwargs)

    def log_message(self, format, *args):
        # Only log actual file requests, skip noise
        if self.path.endswith(".m3u") or self.path.endswith(".m3u8"):
            super().log_message(format, *args)


if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving {SERVE_DIR} on port {PORT}")
        print(f"Playlist URL: http://<your-server-ip>:{PORT}/bo.m3u")
        httpd.serve_forever()
