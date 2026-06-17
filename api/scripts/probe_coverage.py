"""Dev utility: probe data-source coverage for the watchlist.

Why: Finnhub's free tier no longer serves the /stock/candle (historical OHLC)
endpoint, which we need for indicators. This script checks, per ticker, what
each source actually returns from YOUR network + key, so we can lock the data
architecture on facts rather than assumptions.

Run from the api/ directory (reads ../api/.env):

    cd api
    python scripts/probe_coverage.py

It prints a table with three columns per ticker:
  - Finnhub /quote       (current price + daily % change)  -> expected: OK
  - Finnhub /stock/candle (historical OHLC)                -> expected: 403
  - stooq CSV            (daily OHLCV)                      -> candle source

No secrets are printed. Nothing is written anywhere.
"""
from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

# Watchlist: (display name, Finnhub symbol, [candidate stooq symbols])
WATCHLIST = [
    ("Microsoft", "MSFT", ["msft.us"]),
    ("Nvidia", "NVDA", ["nvda.us"]),
    ("AMD", "AMD", ["amd.us"]),
    ("Alphabet", "GOOGL", ["googl.us"]),
    ("ASML", "ASML", ["asml.us"]),
    ("Airbnb", "ABNB", ["abnb.us"]),
    ("Booking", "BKNG", ["bkng.us"]),
    ("Samsung Elec.", "005930.KS", ["005930.kr", "005930.ks"]),
    ("KGHM", "KGH.WA", ["kgh", "kgh.pl"]),
]

UA = "Mozilla/5.0 (probe; stock-dashboard-edu)"


def load_finnhub_key() -> str | None:
    if not ENV_PATH.exists():
        return None
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*FINNHUB_API_KEY\s*=\s*(.+)\s*$", line)
        if m:
            return m.group(1).strip().strip('"').strip("'")
    return None


def http_get(url: str, *, as_json: bool) -> tuple[object, object]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            raw = r.read().decode("utf-8", "replace")
            return r.status, (json.loads(raw) if as_json else raw)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:140]
    except Exception as e:  # noqa: BLE001
        return "ERR", str(e)[:140]


def check_finnhub_quote(sym: str, key: str) -> str:
    s = urllib.parse.quote(sym)
    code, data = http_get(
        f"https://finnhub.io/api/v1/quote?symbol={s}&token={key}", as_json=True
    )
    if isinstance(data, dict):
        c, dp = data.get("c"), data.get("dp")
        if c:
            return f"OK c={c} dp={dp}%"
        return f"empty (HTTP {code})"
    return f"HTTP {code}: {data}"


def check_finnhub_candle(sym: str, key: str) -> str:
    s = urllib.parse.quote(sym)
    now = int(time.time())
    frm = now - 120 * 24 * 3600
    code, data = http_get(
        f"https://finnhub.io/api/v1/stock/candle?symbol={s}&resolution=D&from={frm}&to={now}&token={key}",
        as_json=True,
    )
    if isinstance(data, dict):
        return f"s={data.get('s')} bars={len(data.get('c', []) or [])} (HTTP {code})"
    return f"HTTP {code}: {data}"


def check_stooq(candidates: list[str]) -> str:
    for sym in candidates:
        url = f"https://stooq.com/q/d/l/?s={urllib.parse.quote(sym)}&i=d"
        code, body = http_get(url, as_json=False)
        if isinstance(body, str) and body.startswith("Date,"):
            rows = [r for r in body.strip().splitlines()[1:] if r]
            if rows:
                last = rows[-1].split(",")
                return f"OK '{sym}' rows={len(rows)} last={last[0]} close={last[4] if len(last) > 4 else '?'}"
        # try .pl host for Polish tickers
    # second pass against stooq.pl host
    for sym in candidates:
        url = f"https://stooq.pl/q/d/l/?s={urllib.parse.quote(sym)}&i=d"
        code, body = http_get(url, as_json=False)
        if isinstance(body, str) and body.startswith("Date,"):
            rows = [r for r in body.strip().splitlines()[1:] if r]
            if rows:
                last = rows[-1].split(",")
                return f"OK(pl) '{sym}' rows={len(rows)} last={last[0]}"
    return f"no data for {candidates}"


def main() -> None:
    key = load_finnhub_key()
    print(f"date: {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    print(f"finnhub key loaded: {'yes' if key else 'NO (set FINNHUB_API_KEY in .env)'}\n")

    header = f"{'name':14} {'sym':11} {'finnhub /quote':26} {'finnhub /candle':26} {'stooq CSV'}"
    print(header)
    print("-" * len(header))
    for name, fsym, stooq_syms in WATCHLIST:
        q = check_finnhub_quote(fsym, key) if key else "skip (no key)"
        time.sleep(1.1)  # respect rate limit
        c = check_finnhub_candle(fsym, key) if key else "skip (no key)"
        time.sleep(1.1)
        st = check_stooq(stooq_syms)
        print(f"{name:14} {fsym:11} {q:26} {c:26} {st}")
        time.sleep(0.5)


if __name__ == "__main__":
    main()
