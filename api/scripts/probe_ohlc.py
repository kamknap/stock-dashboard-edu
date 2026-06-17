"""Dev utility: decide the OHLC (candles) source.

Finnhub free has no historical candles, so we need another source. This script:
  1) shows the RAW stooq response (to understand why the first probe saw "no data"),
  2) tests Yahoo Finance's chart endpoint for the full watchlist, including the
     non-US names (Samsung 005930.KS, KGHM KGH.WA).

No key needed, no dependencies (stdlib only). Run from api/:

    python scripts/probe_ohlc.py
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def get(url: str) -> tuple[object, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return "ERR", str(e)


def probe_stooq() -> None:
    print("=== stooq RAW diagnostic ===")
    for host in ("stooq.com", "stooq.pl"):
        for s in ("msft.us", "kgh"):
            code, body = get(f"https://{host}/q/d/l/?s={s}&i=d")
            print(f"{host:10} s={s:8} HTTP {code} | first 160 chars: {body[:160]!r}")
    print()


def probe_yahoo() -> None:
    print("=== Yahoo Finance chart endpoint ===")
    watch = [
        ("Microsoft", "MSFT"),
        ("Nvidia", "NVDA"),
        ("AMD", "AMD"),
        ("Alphabet", "GOOGL"),
        ("ASML", "ASML"),
        ("Airbnb", "ABNB"),
        ("Booking", "BKNG"),
        ("Samsung Elec.", "005930.KS"),
        ("KGHM", "KGH.WA"),
    ]
    for name, sym in watch:
        url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/"
            f"{urllib.parse.quote(sym)}?range=6mo&interval=1d"
        )
        code, body = get(url)
        try:
            d = json.loads(body)
            res = (d.get("chart") or {}).get("result")
            if res:
                ts = res[0].get("timestamp") or []
                closes = (
                    res[0].get("indicators", {}).get("quote", [{}])[0].get("close") or []
                )
                meta = res[0].get("meta", {})
                last_close = next((c for c in reversed(closes) if c is not None), "?")
                print(
                    f"{name:14} {sym:11} OK bars={len(ts):3} "
                    f"last_close={last_close} cur={meta.get('regularMarketPrice')} "
                    f"ccy={meta.get('currency')}"
                )
            else:
                err = (d.get("chart") or {}).get("error")
                print(f"{name:14} {sym:11} NO result (HTTP {code}) err={err}")
        except Exception as e:  # noqa: BLE001
            print(f"{name:14} {sym:11} HTTP {code} parse_err={str(e)[:50]} body={body[:70]!r}")


if __name__ == "__main__":
    probe_stooq()
    probe_yahoo()
