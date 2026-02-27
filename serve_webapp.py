"""
Simple HTTP Server to serve the LinkedIn WebApp
Run this alongside the Telegram bot for mobile posting functionality
"""
import http.server
import socketserver
import os

PORT = 8080
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        # Add CORS headers for Telegram WebApp
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

if __name__ == '__main__':
    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        print("=" * 60)
        print("LINKEDIN WEBAPP SERVER")
        print("=" * 60)
        print(f"\nServer running at: http://localhost:{PORT}")
        print(f"WebApp URL: http://localhost:{PORT}/linkedin_webapp.html")
        print("\nIMPORTANT:")
        print("- For Telegram WebApp to work, you need HTTPS")
        print("- Use ngrok to create HTTPS tunnel:")
        print(f"  1. Run: ngrok http {PORT}")
        print("  2. Copy the HTTPS URL (e.g., https://abc123.ngrok.io)")
        print("  3. Update .env: WEBAPP_URL=https://abc123.ngrok.io")
        print("  4. Restart the Telegram bot")
        print("\nPress Ctrl+C to stop the server")
        print("=" * 60)
        print()

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\nServer stopped.")
