import os
import json
import requests

KV_URL = os.environ.get("KV_REST_API_URL", "")
KV_TOKEN = os.environ.get("KV_REST_API_TOKEN", "")


def _headers():
    return {
        "Authorization": f"Bearer {KV_TOKEN}",
        "Content-Type": "application/json",
    }


def kv_get(key):
    if not KV_URL or not KV_TOKEN:
        return None

    try:
        r = requests.get(f"{KV_URL}/get/{key}", headers=_headers(), timeout=5)
        if r.ok:
            result = r.json().get("result")
            if result is not None:
                return json.loads(result) if isinstance(result, str) else result
    except Exception:
        pass
    return None


def kv_set(key, value):
    if not KV_URL or not KV_TOKEN:
        return False

    try:
        r = requests.post(
            KV_URL,
            headers=_headers(),
            json=["SET", key, json.dumps(value)],
            timeout=5,
        )
        return r.ok
    except Exception:
        return False


def kv_delete(key):
    if not KV_URL or not KV_TOKEN:
        return False

    try:
        r = requests.get(f"{KV_URL}/del/{key}", headers=_headers(), timeout=5)
        return r.ok
    except Exception:
        return False
