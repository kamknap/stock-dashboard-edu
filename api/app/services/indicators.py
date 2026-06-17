"""Technical indicators, computed by hand in pandas (no external TA library).

SMA = rolling mean, EMA = exponential weighted mean (recursive, adjust=False),
RSI = Wilder's smoothing, MACD = EMA(fast) - EMA(slow) with an EMA signal line.
These are the deterministic source of truth for all numbers in the app.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from app.models.analysis import Indicators
from app.models.market import Candles
from app.services.signals import SignalContext

# Periods (kept as module constants; adjust here if the rules change).
SMA_FAST, SMA_SLOW = 20, 50
EMA_FAST, EMA_SLOW = 20, 50
RSI_LENGTH = 14
MACD_FAST, MACD_SLOW, MACD_SIGNAL = 12, 26, 9


@dataclass
class IndicatorResult:
    frame: pd.DataFrame
    latest: Indicators


def to_frame(candles: Candles) -> pd.DataFrame:
    if candles.size == 0:
        return pd.DataFrame()
    return pd.DataFrame(
        {
            "open": candles.open,
            "high": candles.high,
            "low": candles.low,
            "close": candles.close,
            "volume": [float("nan") if v is None else float(v) for v in candles.volume],
        },
        index=pd.DatetimeIndex(candles.dates),
    )


def _sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(window=n, min_periods=n).mean()


def _ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def _rsi(s: pd.Series, n: int) -> pd.Series:
    """Wilder's RSI via exponential smoothing with alpha = 1/n."""
    delta = s.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / n, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / n, adjust=False).mean()
    rs = avg_gain / avg_loss
    # avg_loss == 0 -> rs = inf -> rsi -> 100; handled by the formula.
    return 100.0 - (100.0 / (1.0 + rs))


def compute(candles: Candles) -> IndicatorResult:
    df = to_frame(candles)
    if df.empty:
        return IndicatorResult(df, Indicators())

    close = df["close"]
    df["sma_20"] = _sma(close, SMA_FAST)
    df["sma_50"] = _sma(close, SMA_SLOW)
    df["ema_20"] = _ema(close, EMA_FAST)
    df["ema_50"] = _ema(close, EMA_SLOW)
    df["rsi_14"] = _rsi(close, RSI_LENGTH)
    df["macd"] = _ema(close, MACD_FAST) - _ema(close, MACD_SLOW)
    df["macd_signal"] = df["macd"].ewm(span=MACD_SIGNAL, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    last = df.iloc[-1]
    latest = Indicators(
        as_of=candles.dates[-1],
        close=_val(last["close"]),
        sma_20=_val(last["sma_20"]),
        sma_50=_val(last["sma_50"]),
        ema_20=_val(last["ema_20"]),
        ema_50=_val(last["ema_50"]),
        rsi_14=_val(last["rsi_14"]),
        macd=_val(last["macd"]),
        macd_signal=_val(last["macd_signal"]),
        macd_hist=_val(last["macd_hist"]),
    )
    return IndicatorResult(df, latest)


def build_context(frame: pd.DataFrame) -> SignalContext | None:
    """Turn the indicator frame into a pandas-free context for the signal rules."""
    if frame is None or frame.empty:
        return None
    last = frame.iloc[-1]
    prev = frame.iloc[-2] if len(frame) >= 2 else None

    def cross_up(a: str, b: str) -> bool:
        if prev is None:
            return False
        pa, pb, ca, cb = _g(prev, a), _g(prev, b), _g(last, a), _g(last, b)
        if None in (pa, pb, ca, cb):
            return False
        return pa <= pb and ca > cb

    def cross_down(a: str, b: str) -> bool:
        if prev is None:
            return False
        pa, pb, ca, cb = _g(prev, a), _g(prev, b), _g(last, a), _g(last, b)
        if None in (pa, pb, ca, cb):
            return False
        return pa >= pb and ca < cb

    return SignalContext(
        close=_g(last, "close"),
        ema_50=_g(last, "ema_50"),
        sma_20=_g(last, "sma_20"),
        sma_50=_g(last, "sma_50"),
        rsi_14=_g(last, "rsi_14"),
        macd=_g(last, "macd"),
        macd_signal=_g(last, "macd_signal"),
        sma_cross_up=cross_up("sma_20", "sma_50"),
        sma_cross_down=cross_down("sma_20", "sma_50"),
        macd_cross_up=cross_up("macd", "macd_signal"),
        macd_cross_down=cross_down("macd", "macd_signal"),
    )


def _val(x: object) -> float | None:
    if x is None or pd.isna(x):
        return None
    return float(x)


def _g(row: pd.Series, col: str) -> float | None:
    if row is None or col not in row.index:
        return None
    return _val(row[col])
