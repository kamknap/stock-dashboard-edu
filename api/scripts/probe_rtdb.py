"""Dev utility: verify Firebase Realtime Database connectivity (write + read).

The sandbox can't reach Firebase, so run this on your machine. It reads
FIREBASE_DB_URL and GOOGLE_APPLICATION_CREDENTIALS from ../api/.env, initialises
the Admin SDK, writes a probe value under reports/_probe, reads it back, then
deletes it. No secrets are printed.

    cd api
    python scripts/probe_rtdb.py
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def load(key: str) -> str | None:
    if not ENV_PATH.exists():
        return None
    for line in ENV_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(rf"\s*{key}\s*=\s*(.*)\s*$", line)
        if m:
            return m.group(1).strip().strip('"').strip("'")
    return None


def main() -> None:
    url = load("FIREBASE_DB_URL")
    cred = load("GOOGLE_APPLICATION_CREDENTIALS")
    print(f"FIREBASE_DB_URL: {url or 'MISSING'}")
    print(f"GOOGLE_APPLICATION_CREDENTIALS: {cred or 'MISSING'}")
    if not url or not cred:
        print("\n-> Set BOTH in api/.env, then re-run.")
        return

    cred_path = Path(cred)
    print(f"credentials file exists: {cred_path.exists()}")
    if not cred_path.exists():
        print("\n-> The path is wrong or the file name is incomplete (must end in .json).")
        return
    try:
        info = json.loads(cred_path.read_text(encoding="utf-8"))
        print(f"service account: project_id={info.get('project_id')} client_email={info.get('client_email')}")
    except Exception as exc:  # noqa: BLE001
        print(f"-> credentials file is not valid JSON: {exc}")
        return

    try:
        import firebase_admin
        from firebase_admin import credentials, db
    except ImportError:
        print("\n-> firebase-admin not installed. Run: pip install -r requirements-dev.txt")
        return

    if not firebase_admin._apps:
        firebase_admin.initialize_app(
            credentials.Certificate(str(cred_path)), {"databaseURL": url}
        )

    ref = db.reference("reports/_probe")
    payload = {"ok": True, "ts": datetime.now(timezone.utc).isoformat()}
    try:
        ref.set(payload)
        back = ref.get()
        print(f"write+read OK: {back == payload} -> {back}")
        ref.delete()
        print("probe cleaned up. RTDB is working.")
    except Exception as exc:  # noqa: BLE001
        print(f"-> RTDB call failed: {exc}")


if __name__ == "__main__":
    main()
