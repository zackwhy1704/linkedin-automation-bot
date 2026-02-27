#!/usr/bin/env python3
"""
Simple Web Server for LinkedIn WebApp
Serves the mobile webapp for Telegram bot
Uses only Python built-in modules - no external dependencies
"""

import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class WebAppHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        print(f"[WebApp] {self.address_string()} - {format % args}")

    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.lstrip("/")

        # Root or health check
        if path == "" or path == "health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(b'{"status": "healthy", "service": "linkedin-bot-webapp"}')
            return

        # Serve linkedin_webapp.html (with query params)
        if path == "linkedin_webapp.html" or path.startswith("linkedin_webapp.html"):
            file_path = os.path.join(BASE_DIR, "linkedin_webapp.html")
            if not os.path.exists(file_path):
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"<h1>Error: linkedin_webapp.html not found</h1>")
                return
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(content)
            return

        # Test page
        if path == "test":
            html = b"""<!DOCTYPE html>
<html><head><title>WebApp Test</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
</head><body>
<h1>Telegram WebApp Test</h1>
<p>Server is working!</p>
<script>let tg=window.Telegram.WebApp;tg.expand();tg.ready();</script>
</body></html>"""
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(html)
            return

        # 404
        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"Not found")


if __name__ == "__main__":
    port = int(os.getenv("WEBAPP_PORT", 8080))
    host = os.getenv("WEBAPP_HOST", "0.0.0.0")

    print(f"[WebApp] Starting server on http://{host}:{port}")
    print(f"[WebApp] Serving: {BASE_DIR}/linkedin_webapp.html")
    print(f"[WebApp] Health check: http://localhost:{port}/health")
    print(f"[WebApp] Test page:    http://localhost:{port}/test")
    print(f"[WebApp] Press Ctrl+C to stop")

    server = HTTPServer((host, port), WebAppHandler)
    server.serve_forever()
