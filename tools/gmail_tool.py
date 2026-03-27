import json
import base64
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from tools.kv_store import kv_get, kv_set


def _get_service():
    token_data = kv_get("gmail:token")
    if not token_data:
        return None

    try:
        creds = Credentials.from_authorized_user_info(token_data)
    except Exception:
        return None

    try:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            updated_token = {
                "token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri": creds.token_uri,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "scopes": list(creds.scopes) if creds.scopes else token_data.get("scopes", []),
            }
            kv_set("gmail:token", updated_token)
    except Exception:
        return None

    try:
        return build("gmail", "v1", credentials=creds, cache_discovery=False)
    except Exception:
        return None


NOT_CONFIGURED = {"success": False, "error": "Gmail not connected. Send /login to connect your Gmail account."}


def _get_email_headers(service, msg_id):
    """Fetch metadata headers for a single message."""
    m = service.users().messages().get(
        userId="me",
        id=msg_id,
        format="metadata",
        metadataHeaders=["Subject", "From", "To", "Date", "Message-ID"]
    ).execute()
    headers = {h["name"]: h["value"] for h in m["payload"]["headers"]}
    return {
        "id": msg_id,
        "subject": headers.get("Subject", "(no subject)"),
        "from": headers.get("From", "unknown"),
        "to": headers.get("To", ""),
        "date": headers.get("Date", ""),
        "snippet": m.get("snippet", ""),
        "labels": m.get("labelIds", []),
    }


def read_emails(count=5):
    service = _get_service()
    if not service:
        return NOT_CONFIGURED

    try:
        results = service.users().messages().list(userId="me", maxResults=count).execute()
        messages = results.get("messages", [])

        emails = []
        for msg in messages:
            emails.append(_get_email_headers(service, msg["id"]))

        return {"success": True, "count": len(emails), "emails": emails}

    except Exception as e:
        return {"success": False, "error": str(e)}


def send_email(to, subject, body):
    service = _get_service()
    if not service:
        return NOT_CONFIGURED

    try:
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        result = service.users().messages().send(
            userId="me",
            body={"raw": raw}
        ).execute()

        return {"success": True, "message_id": result["id"]}

    except Exception as e:
        return {"success": False, "error": str(e)}


def search_emails(query):
    service = _get_service()
    if not service:
        return NOT_CONFIGURED

    try:
        results = service.users().messages().list(userId="me", q=query, maxResults=10).execute()
        messages = results.get("messages", [])

        emails = []
        for msg in messages:
            emails.append(_get_email_headers(service, msg["id"]))

        return {"success": True, "count": len(emails), "emails": emails}

    except Exception as e:
        return {"success": False, "error": str(e)}


def get_email(message_id):
    """Get the full content of a specific email."""
    service = _get_service()
    if not service:
        return NOT_CONFIGURED

    try:
        m = service.users().messages().get(userId="me", id=message_id, format="full").execute()
        headers = {h["name"]: h["value"] for h in m["payload"]["headers"]}

        body = ""
        payload = m["payload"]
        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain" and "data" in part.get("body", {}):
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                    break
        elif "data" in payload.get("body", {}):
            body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

        if len(body) > 1500:
            body = body[:1500] + "... (truncated)"

        return {
            "success": True,
            "id": message_id,
            "subject": headers.get("Subject", "(no subject)"),
            "from": headers.get("From", "unknown"),
            "to": headers.get("To", ""),
            "date": headers.get("Date", ""),
            "body": body or m.get("snippet", ""),
            "labels": m.get("labelIds", []),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def reply_to_email(message_id, body):
    """Reply to a specific email."""
    service = _get_service()
    if not service:
        return NOT_CONFIGURED

    try:
        original = service.users().messages().get(
            userId="me", id=message_id, format="metadata",
            metadataHeaders=["Subject", "From", "To", "Message-ID"]
        ).execute()
        headers = {h["name"]: h["value"] for h in original["payload"]["headers"]}
        thread_id = original.get("threadId", "")

        reply = MIMEText(body)
        reply["to"] = headers.get("From", "")
        subject = headers.get("Subject", "")
        reply["subject"] = subject if subject.lower().startswith("re:") else f"Re: {subject}"
        reply["In-Reply-To"] = headers.get("Message-ID", "")
        reply["References"] = headers.get("Message-ID", "")

        raw = base64.urlsafe_b64encode(reply.as_bytes()).decode()

        result = service.users().messages().send(
            userId="me",
            body={"raw": raw, "threadId": thread_id}
        ).execute()

        return {"success": True, "message_id": result["id"], "replied_to": headers.get("From", "")}

    except Exception as e:
        return {"success": False, "error": str(e)}


def trash_email(message_id):
    """Move an email to trash."""
    service = _get_service()
    if not service:
        return NOT_CONFIGURED

    try:
        service.users().messages().trash(userId="me", id=message_id).execute()
        return {"success": True, "message_id": message_id, "action": "trashed"}

    except Exception as e:
        return {"success": False, "error": str(e)}


def mark_as_read(message_id):
    """Mark an email as read by removing UNREAD label."""
    service = _get_service()
    if not service:
        return NOT_CONFIGURED

    try:
        service.users().messages().modify(
            userId="me", id=message_id,
            body={"removeLabelIds": ["UNREAD"]}
        ).execute()
        return {"success": True, "message_id": message_id, "action": "marked_read"}

    except Exception as e:
        return {"success": False, "error": str(e)}


def mark_as_unread(message_id):
    """Mark an email as unread by adding UNREAD label."""
    service = _get_service()
    if not service:
        return NOT_CONFIGURED

    try:
        service.users().messages().modify(
            userId="me", id=message_id,
            body={"addLabelIds": ["UNREAD"]}
        ).execute()
        return {"success": True, "message_id": message_id, "action": "marked_unread"}

    except Exception as e:
        return {"success": False, "error": str(e)}


def star_email(message_id):
    """Star an email."""
    service = _get_service()
    if not service:
        return NOT_CONFIGURED

    try:
        service.users().messages().modify(
            userId="me", id=message_id,
            body={"addLabelIds": ["STARRED"]}
        ).execute()
        return {"success": True, "message_id": message_id, "action": "starred"}

    except Exception as e:
        return {"success": False, "error": str(e)}


def unstar_email(message_id):
    """Unstar an email."""
    service = _get_service()
    if not service:
        return NOT_CONFIGURED

    try:
        service.users().messages().modify(
            userId="me", id=message_id,
            body={"removeLabelIds": ["STARRED"]}
        ).execute()
        return {"success": True, "message_id": message_id, "action": "unstarred"}

    except Exception as e:
        return {"success": False, "error": str(e)}


def list_labels():
    """List all Gmail labels."""
    service = _get_service()
    if not service:
        return NOT_CONFIGURED

    try:
        results = service.users().labels().list(userId="me").execute()
        labels = results.get("labels", [])
        return {
            "success": True,
            "count": len(labels),
            "labels": [
                {"id": l["id"], "name": l["name"], "type": l.get("type", "")}
                for l in labels
            ]
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def email_stats():
    """Get email statistics: unread count, today's emails, starred count, total inbox."""
    service = _get_service()
    if not service:
        return NOT_CONFIGURED

    try:
        stats = {}

        unread = service.users().messages().list(
            userId="me", q="is:unread", maxResults=1
        ).execute()
        stats["unread"] = unread.get("resultSizeEstimate", 0)

        today = service.users().messages().list(
            userId="me", q="newer_than:1d", maxResults=1
        ).execute()
        stats["today"] = today.get("resultSizeEstimate", 0)

        starred = service.users().messages().list(
            userId="me", q="is:starred", maxResults=1
        ).execute()
        stats["starred"] = starred.get("resultSizeEstimate", 0)

        inbox = service.users().messages().list(
            userId="me", q="in:inbox", maxResults=1
        ).execute()
        stats["inbox_total"] = inbox.get("resultSizeEstimate", 0)

        sent_today = service.users().messages().list(
            userId="me", q="in:sent newer_than:1d", maxResults=1
        ).execute()
        stats["sent_today"] = sent_today.get("resultSizeEstimate", 0)

        return {"success": True, "stats": stats}

    except Exception as e:
        return {"success": False, "error": str(e)}


def forward_email(message_id, to):
    """Forward an email to another recipient."""
    service = _get_service()
    if not service:
        return NOT_CONFIGURED

    try:
        original = service.users().messages().get(
            userId="me", id=message_id, format="full"
        ).execute()
        headers = {h["name"]: h["value"] for h in original["payload"]["headers"]}

        body = ""
        payload = original["payload"]
        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain" and "data" in part.get("body", {}):
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                    break
        elif "data" in payload.get("body", {}):
            body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

        if not body:
            body = original.get("snippet", "")

        fwd_body = (
            f"---------- Forwarded message ----------\n"
            f"From: {headers.get('From', 'unknown')}\n"
            f"Date: {headers.get('Date', '')}\n"
            f"Subject: {headers.get('Subject', '(no subject)')}\n\n"
            f"{body}"
        )

        fwd = MIMEText(fwd_body)
        fwd["to"] = to
        fwd["subject"] = f"Fwd: {headers.get('Subject', '(no subject)')}"
        raw = base64.urlsafe_b64encode(fwd.as_bytes()).decode()

        result = service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()

        return {"success": True, "message_id": result["id"], "forwarded_to": to}

    except Exception as e:
        return {"success": False, "error": str(e)}


def archive_email(message_id):
    """Archive an email by removing the INBOX label."""
    service = _get_service()
    if not service:
        return NOT_CONFIGURED

    try:
        service.users().messages().modify(
            userId="me", id=message_id,
            body={"removeLabelIds": ["INBOX"]}
        ).execute()
        return {"success": True, "message_id": message_id, "action": "archived"}

    except Exception as e:
        return {"success": False, "error": str(e)}


def untrash_email(message_id):
    """Recover an email from trash."""
    service = _get_service()
    if not service:
        return NOT_CONFIGURED

    try:
        service.users().messages().untrash(userId="me", id=message_id).execute()
        return {"success": True, "message_id": message_id, "action": "untrashed"}

    except Exception as e:
        return {"success": False, "error": str(e)}


def list_drafts():
    """List all draft emails."""
    service = _get_service()
    if not service:
        return NOT_CONFIGURED

    try:
        results = service.users().drafts().list(userId="me", maxResults=10).execute()
        drafts = results.get("drafts", [])

        draft_list = []
        for d in drafts:
            draft = service.users().drafts().get(
                userId="me", id=d["id"], format="metadata"
            ).execute()
            msg = draft.get("message", {})
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            draft_list.append({
                "draft_id": d["id"],
                "to": headers.get("To", ""),
                "subject": headers.get("Subject", "(no subject)"),
                "snippet": msg.get("snippet", ""),
            })

        return {"success": True, "count": len(draft_list), "drafts": draft_list}

    except Exception as e:
        return {"success": False, "error": str(e)}


def create_draft(to, subject, body):
    """Create a draft email without sending it."""
    service = _get_service()
    if not service:
        return NOT_CONFIGURED

    try:
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        draft = service.users().drafts().create(
            userId="me",
            body={"message": {"raw": raw}}
        ).execute()

        return {"success": True, "draft_id": draft["id"]}

    except Exception as e:
        return {"success": False, "error": str(e)}

