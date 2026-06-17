"""Yahoo Finance market-data service.

Single source of truth for raw market data (chosen in phase 2 after Finnhub's
free tier proved to lack historical candles). One chart request per symbol
yields both the OHLCV series (for indicators / movers) and the latest price
(for snapshots), so we parse it once and cache it as a `ChartData`.

This is the shared fetch layer reused by the scheduled report, the chat tool,
and the Top movers ranking. All numbers are computed deterministically in
Python; this module only fetches and structures the data.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

from app.config import Settings, get_settings
from app.models.market import Candles, Snapshot
from app.services.cache import TTLCache

# A browser-like UA; Yahoo's public chart endpoint rejects some default clients.
_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}
_HOSTS = ("query1.finance.yahoo.com", "query2.finance.yahoo.com")
# HTTP statuses worth retrying / failing over on.
_TRANSIENT = {429, 500, 502, 503, 504}


class MarketDataError(Exception):
    """Raised when market data for a symbol cannot be retrieved or parsed."""


@dataclass
class ChartData:
    """Parsed chart payload: the candle series plus the live-price scalars."""

    candles: Candles
    market_price: float | None
    previous_close: float | None


class YahooMarketData:
    def __init__(
        self,
        client: httpx.AsyncClient,
        cache: TTLCache,
        settings: Settings | None = None,
    ) -> None:
        self._client = client
        self._cache = cache
        self._settings = settings or get_settings()

    # ---- public API ----
    async def get_candles(
        self,
        symbol: str,
        *,
        range: str | None = None,
        interval: str | None = None,
    ) -> Candles:
        return (await self._get_chart(symbol, range, interval)).candles

    async def get_snapshot(
        self, symbol: str, *, range: str | None = None, interval: str | None = None
    ) -> Snapshot:
        """Latest price + deterministic daily % change, derived from the chart."""
        return self._snapshot_from(await self._get_chart(symbol, range, interval))

    async def get_snapshots(self, symbols: list[str]) -> dict[str, Snapshot | None]:
        """Fetch snapshots for many symbols with bounded concurrency.

        A failing symbol maps to None instead of failing the whole batch.
        """
        sem = asyncio.Semaphore(self._settings.market_max_concurrency)

        async def one(sym: str) -> tuple[str, Snapshot | None]:
            async with sem:
                try:
                    return sym, await self.get_snapshot(sym)
                except MarketDataError:
                    return sym, None

        results = await asyncio.gather(*(one(s) for s in symbols))
        return dict(results)

    # ---- internals ----
    async def _get_chart(
        self, symbol: str, range: str | None, interval: str | None
    ) -> ChartData:
        rng = range or self._settings.market_default_range
        itv = interval or self._settings.market_default_interval
        return await self._cache.get_or_set(
            ("chart", symbol, rng, itv),
            lambda: self._fetch_chart(symbol, rng, itv),
        )

    async def _fetch_chart(self, symbol: str, rng: str, itv: str) -> ChartData:
        payload = await self._request_chart(symbol, rng, itv)
        return self._parse_chart(symbol, rng, itv, payload)

    async def _request_chart(self, symbol: str, rng: str, itv: str) -> dict:
        params = {"range": rng, "interval": itv}
        last_error: str | None = None
        for host in _HOSTS:
            url = f"https://{host}/v8/finance/chart/{symbol}"
            for attempt in range(self._settings.market_max_retries):
                try:
                    resp = await self._client.get(
                        url,
                        params=params,
                        headers=_DEFAULT_HEADERS,
                        timeout=self._settings.http_timeout_seconds,
                    )
                except httpx.HTTPError as exc:
                    last_error = f"transport error: {exc!r}"
                    await asyncio.sleep(0.4 * (attempt + 1))
                    continue
                if resp.status_code == 200:
                    return resp.json()
                if resp.status_code in _TRANSIENT:
                    last_error = f"HTTP {resp.status_code}"
                    await asyncio.sleep(0.4 * (attempt + 1))
                    continue
                # Non-transient (e.g. 404 unknown symbol): stop early.
                raise MarketDataError(f"{symbol}: HTTP {resp.status_code}")
        raise MarketDataError(f"{symbol}: request failed ({last_error})")

    @staticmethod
    def _parse_chart(symbol: str, rng: str, itv: str, payload: dict) -> ChartData:
        chart = payload.get("chart") or {}
        if chart.get("error"):
            raise MarketDataError(f"{symbol}: {chart['error']}")
        results = chart.get("result") or []
        if not results:
            raise MarketDataError(f"{symbol}: empty chart result")
        result = results[0]
        meta = result.get("meta") or {}
        timestamps = result.get("timestamp") or []
        quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]

        opens = quote.get("open") or []
        highs = quote.get("high") or []
        lows = quote.get("low") or []
        closes = quote.get("close") or []
        volumes = quote.get("volume") or []

        candles = Candles(
            symbol=symbol,
            currency=meta.get("currency"),
            interval=itv,
            range=rng,
        )
        for i, ts in enumerate(timestamps):
            close = closes[i] if i < len(closes) else None
            if close is None:  # skip gaps / partial trailing rows
                continue
            candles.dates.append(datetime.fromtimestamp(ts, tz=timezone.utc))
            candles.open.append(_num(opens, i, close))
            candles.high.append(_num(highs, i, close))
            candles.low.append(_num(lows, i, close))
            candles.close.append(float(close))
            vol = volumes[i] if i < len(volumes) else None
            candles.volume.append(int(vol) if vol is not None else None)

        if not candles.close:
            raise MarketDataError(f"{symbol}: no usable candles")

        return ChartData(
            candles=candles,
            market_price=meta.get("regularMarketPrice"),
            previous_close=meta.get("previousClose") or meta.get("chartPreviousClose"),
        )

    @staticmethod
    def _snapshot_from(chart: ChartData) -> Snapshot:
        candles = chart.candles
        closes = candles.close
        price = chart.market_price if chart.market_price is not None else closes[-1]

        # Previous close = the prior DAILY candle. The chart's last bar is the
        # current/most-recent session, so closes[-2] is the prior session close.
        # (Yahoo's meta.previousClose is unreliable for multi-month ranges, where
        # it returns the close before the whole window -> a bogus "daily" move.)
        if len(closes) >= 2:
            prev = closes[-2]
        else:
            prev = chart.previous_close

        change = change_pct = None
        if price is not None and prev:
            change = float(price) - float(prev)
            change_pct = change / float(prev) * 100.0

        return Snapshot(
            symbol=candles.symbol,
            currency=candles.currency,
            price=float(price) if price is not None else None,
            previous_close=float(prev) if prev is not None else None,
            change=change,
            change_pct=change_pct,
            as_of=datetime.now(timezone.utc),
        )


def _num(arr: list, i: int, fallback: float) -> float:
    """Return arr[i] as float, falling back when Yahoo leaves a null."""
    if i < len(arr) and arr[i] is not None:
        return float(arr[i])
    return float(fallback)
