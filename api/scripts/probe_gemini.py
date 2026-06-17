"""Dev utility: verify the Gemini API key + Google Search grounding locally.

The sandbox cannot reach Gemini, so run this on your machine to confirm the key
works and grounding returns sources. Run from the api/ directory (reads ../api/.env):

    python scripts/probe_gemini.py

Prints the HTTP status, the start of the model's text, and the grounding
sources it cited. No secrets are printed.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
MODEL = "gemini-2.5-flash"
PROMPT = (
    "In one or two sentences, what is the most recent news about Nvidia (NVDA) "
    "as of today? Use Google Search and cite sources."
)


def load_key() -> str | None:
    if not ENV_PATH.exists():
        return None
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*GEMINI_API_KEY\s*=\s*(.+)\s*$", line)
        if m:
            return m.group(1).strip().strip('"').strip("'")
    return None


def main() -> None:
    key = load_key()
    print(f"GEMINI_API_KEY loaded: {'yes' if key else 'NO (set it in .env)'}")
    if not key:
        return

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    body = {
        "contents": [{"parts": [{"text": PROMPT}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {"temperature": 0.4},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            status, payload = r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode()[:300]}")
        return
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: {e}")
        return

    print(f"HTTP {status}")
    cand = (payload.get("candidates") or [{}])[0]
    parts = (cand.get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
    print(f"\nmodel text (first 400 chars):\n{text[:400]}")

    meta = cand.get("groundingMetadata") or {}
    chunks = meta.get("groundingChunks") or []
    queries = meta.get("webSearchQueries") or []
    print(f"\nsearch queries: {queries}")
    print(f"grounding sources ({len(chunks)}):")
    for c in chunks[:8]:
        web = c.get("web") or {}
        print(f"  - {web.get('title')} | {web.get('uri')}")


if __name__ == "__main__":
    main()
