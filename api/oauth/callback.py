from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tools.kv_store import kv_set

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
BOT_BASE_URL = os.environ.get("BOT_BASE_URL", "")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
REDIRECT_URI = f"{BOT_BASE_URL}/api/oauth/callback"


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        import requests

        params = parse_qs(urlparse(self.path).query)
        code = params.get("code", [None])[0]
        chat_id = params.get("state", [None])[0]

        error = params.get("error", [None])[0]
        if error:
            self._respond(400, f"<html><body><h2>Authorization denied: {error}</h2><p>Go back to Telegram and try again.</p></body></html>")
            return

        if not code or not chat_id:
            self._respond(400, "<html><body><h2>Missing authorization code. Please try /login again in Telegram.</h2></body></html>")
            return

        try:
            token_resp = requests.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "redirect_uri": REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
                timeout=10,
            )
        except Exception:
            self._respond(500, "<html><body><h2>Failed to connect to Google. Please try again.</h2></body></html>")
            return

        if not token_resp.ok:
            self._respond(500, "<html><body><h2>Token exchange failed. Please try /login again in Telegram.</h2></body></html>")
            return

        token_data = token_resp.json()

        token_obj = {
            "token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token"),
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "scopes": SCOPES,
        }

        if not kv_set("gmail:token", token_obj):
            self._respond(500, "<html><body><h2>Failed to save token. Check Vercel KV configuration.</h2></body></html>")
            return

        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id": int(chat_id), "text": "Gmail connected successfully! You can now use email commands."},
                timeout=10,
            )
        except Exception:
            pass

        self._respond(200, "<html><body><h2>Gmail connected!</h2><p>You can close this tab and go back to Telegram.</p></body></html>")

    def _respond(self, status, body):
        self.send_response(status)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, format, *args):
        pass

