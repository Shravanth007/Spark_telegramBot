import json
from tools.kv_store import kv_get, kv_set, kv_delete


def _get_all_notes():
    """Get the notes dict from KV."""
    return kv_get("user:notes") or {}


def _save_all_notes(notes):
    """Save the notes dict to KV."""
    return kv_set("user:notes", notes)


def save_note(title, content):
    """Save a note with a title and content."""
    if not title:
        return {"success": False, "error": "Note title is required."}

    notes = _get_all_notes()
    notes[title] = content
    if _save_all_notes(notes):
        return {"success": True, "title": title, "action": "saved"}
    return {"success": False, "error": "Failed to save note."}


def get_note(title):
    if not title:
        return {"success": False, "error": "Note title is required."}

    notes = _get_all_notes()
    if title in notes:
        return {"success": True, "title": title, "content": notes[title]}

    matches = [k for k in notes if title.lower() in k.lower()]
    if matches:
        return {
            "success": True,
            "title": matches[0],
            "content": notes[matches[0]],
            "note": f"Partial match. Did you mean '{matches[0]}'?"
        }

    return {"success": False, "error": f"Note '{title}' not found."}


def list_notes():
    notes = _get_all_notes()
    if not notes:
        return {"success": True, "count": 0, "notes": [], "note": "No notes saved yet."}

    return {
        "success": True,
        "count": len(notes),
        "notes": [
            {"title": k, "preview": v[:100] + "..." if len(v) > 100 else v}
            for k, v in notes.items()
        ]
    }


def delete_note(title):
    if not title:
        return {"success": False, "error": "Note title is required."}

    notes = _get_all_notes()
    if title not in notes:
        return {"success": False, "error": f"Note '{title}' not found."}

    del notes[title]
    if _save_all_notes(notes):
        return {"success": True, "title": title, "action": "deleted"}
    return {"success": False, "error": "Failed to delete note."}

