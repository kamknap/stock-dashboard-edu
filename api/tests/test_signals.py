"""Unit tests for the explicit signal rules (pandas-free)."""
from __future__ import annotations

from app.services.signals import SignalContext, evaluate


def codes(ctx: SignalContext) -> set[str]:
    return {s.code for s in evaluate(ctx)}


def test_empty_context_yields_nothing() -> None:
    assert evaluate(SignalContext()) == []


def test_trend_context_above_and_below_ema50() -> None:
    assert "above_ema50" in codes(SignalContext(close=110.0, ema_50=100.0))
    assert "below_ema50" in codes(SignalContext(close=90.0, ema_50=100.0))


def test_oversold_in_uptrend_combo() -> None:
    found = codes(SignalContext(close=110.0, ema_50=100.0, rsi_14=25.0))
    assert "rsi_oversold" in found
    assert "oversold_in_uptrend" in found
    assert "above_ema50" in found


def test_overbought_in_downtrend_combo() -> None:
    found = codes(SignalContext(close=90.0, ema_50=100.0, rsi_14=80.0))
    assert "rsi_overbought" in found
    assert "overbought_in_downtrend" in found


def test_rsi_overbought_without_downtrend_has_no_combo() -> None:
    found = codes(SignalContext(close=110.0, ema_50=100.0, rsi_14=80.0))
    assert "rsi_overbought" in found
    assert "overbought_in_downtrend" not in found


def test_sma_and_macd_crosses() -> None:
    up = codes(SignalContext(sma_cross_up=True, macd_cross_up=True))
    assert {"sma_bullish_cross", "macd_bullish_cross"} <= up
    down = codes(SignalContext(sma_cross_down=True, macd_cross_down=True))
    assert {"sma_bearish_cross", "macd_bearish_cross"} <= down


def test_direction_field_is_technical_only() -> None:
    sigs = evaluate(SignalContext(close=110.0, ema_50=100.0))
    assert all(s.direction in {"up", "down", "neutral"} for s in sigs)
