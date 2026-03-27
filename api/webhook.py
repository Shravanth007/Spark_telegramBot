from http.server import BaseHTTPRequestHandler
import json
import os
import re
import sys
from urllib.parse import urlencode

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import run_agent
from tools.kv_store import kv_delete

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
BOT_BASE_URL = os.environ.get("BOT_BASE_URL", "")

ALLOWED_CHAT_IDS = os.environ.get("ALLOWED_CHAT_IDS", "")
_allowed_ids = set()
if ALLOWED_CHAT_IDS:
    _allowed_ids = {int(cid.strip()) for cid in ALLOWED_CHAT_IDS.split(",") if cid.strip()}

GMAIL_SCOPES = "https://www.googleapis.com/auth/gmail.modify"


def _clean_markdown(text):
    """Convert LLM markdown to clean plain text for Telegram."""
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'(?<!\w)_(.+?)_(?!\w)', r'\1', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    return text


def send_message(chat_id, text):
    import requests

    cleaned = _clean_markdown(text)
    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={"chat_id": chat_id, "text": cleaned},
        timeout=10,
    )


def send_typing(chat_id):
    import requests
    requests.post(
        f"{TELEGRAM_API}/sendChatAction",
        json={"chat_id": chat_id, "action": "typing"},
        timeout=5,
    )


def build_oauth_url(chat_id):
    """Build Google OAuth2 authorization URL."""
    params = urlencode({
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": f"{BOT_BASE_URL}/api/oauth/callback",
        "response_type": "code",
        "scope": GMAIL_SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "state": str(chat_id),
    })
    return f"https://accounts.google.com/o/oauth2/v2/auth?{params}"


def handle_command(chat_id, text):
    """Handle bot commands. Returns True if a command was handled."""
    command = text.strip().split()[0].lower()

    if command == "/start":
        send_message(chat_id,
            "Hey! I'm your personal AI assistant.\n\n"
            "Here's what I can do:\n"
            "- GitHub: manage repos, issues, PRs, branches, and more\n"
            "- Gmail: read, send, search, reply, forward emails\n"
            "- Web: search the internet, summarize articles\n"
            "- Notes: save and manage personal notes\n"
            "- Or just chat!\n\n"
            "Commands:\n"
            "/login - Connect your Gmail account\n"
            "/logout - Disconnect Gmail\n\n"
            "Just type naturally and I'll figure out what you need."
        )
        return True

    if command == "/login":
        if not GOOGLE_CLIENT_ID or not BOT_BASE_URL:
            send_message(chat_id, "Gmail OAuth is not configured on the server.")
            return True

        url = build_oauth_url(chat_id)
        send_message(chat_id, f"Click the link below to connect your Gmail account:\n\n{url}")
        return True

    if command == "/logout":
        kv_delete("gmail:token")
        send_message(chat_id, "Gmail disconnected. Send /login to reconnect.")
        return True

    return False


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(content_length))

        message = body.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "")

        if chat_id and text:
            if _allowed_ids and chat_id not in _allowed_ids:
                try:
                    send_message(chat_id, "You are not authorized to use this bot.")
                except Exception:
                    pass
            else:
                try:
                    if text.strip().startswith("/"):
                        if not handle_command(chat_id, text):
                            send_message(chat_id, "Unknown command. Just type naturally or use /start for help.")
                    else:
                        send_typing(chat_id)
                        reply = run_agent(text, chat_id=chat_id)
                        send_message(chat_id, reply)
                except Exception as e:
                    try:
                        send_message(chat_id, f"Something went wrong: {str(e)}")
                    except Exception:
                        pass

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"ok": True}).encode())

    def log_message(self, format, *args):
        pass

