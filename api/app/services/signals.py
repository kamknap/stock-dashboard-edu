"""Explicit, deterministic signal rules.

Signals are plain rules over already-computed indicators, not model opinions.
`direction` describes the technical reading only; nothing here is a buy/sell
recommendation. The chat/report layers always wrap these with the disclaimer.

`SignalContext` is a pandas-free snapshot of the latest (and cross) values so
these rules can be unit-tested in isolation.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.models.analysis import Signal


@dataclass
class SignalContext:
    close: float | None = None
    ema_50: float | None = None
    sma_20: float | None = None
    sma_50: float | None = None
    rsi_14: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    sma_cross_up: bool = False
    sma_cross_down: bool = False
    macd_cross_up: bool = False
    macd_cross_down: bool = False


RSI_OVERSOLD = 30.0
RSI_OVERBOUGHT = 70.0


def evaluate(ctx: SignalContext) -> list[Signal]:
    """Apply the rule set in a fixed order; return all that match."""
    out: list[Signal] = []

    # --- trend context vs EMA50 ---
    if ctx.close is not None and ctx.ema_50 is not None:
        if ctx.close > ctx.ema_50:
            out.append(
                Signal(
                    code="above_ema50",
                    label="Price above EMA50",
                    detail="Last close is above the 50-period EMA (longer-term uptrend context).",
                    direction="up",
                )
            )
        else:
            out.append(
                Signal(
                    code="below_ema50",
                    label="Price below EMA50",
                    detail="Last close is below the 50-period EMA (longer-term downtrend context).",
                    direction="down",
                )
            )

    # --- RSI extremes ---
    if ctx.rsi_14 is not None:
        if ctx.rsi_14 < RSI_OVERSOLD:
            out.append(
                Signal(
                    code="rsi_oversold",
                    label="RSI oversold",
                    detail=f"RSI(14) is {ctx.rsi_14:.1f}, below {RSI_OVERSOLD:.0f}.",
                    direction="neutral",
                )
            )
        elif ctx.rsi_14 > RSI_OVERBOUGHT:
            out.append(
                Signal(
                    code="rsi_overbought",
                    label="RSI overbought",
                    detail=f"RSI(14) is {ctx.rsi_14:.1f}, above {RSI_OVERBOUGHT:.0f}.",
                    direction="neutral",
                )
            )

    # --- combined RSI + trend ---
    if ctx.rsi_14 is not None and ctx.close is not None and ctx.ema_50 is not None:
        if ctx.rsi_14 < RSI_OVERSOLD and ctx.close > ctx.ema_50:
            out.append(
                Signal(
                    code="oversold_in_uptrend",
                    label="Oversold within an uptrend",
                    detail="RSI(14) below 30 while price holds above EMA50.",
                    direction="up",
                )
            )
        if ctx.rsi_14 > RSI_OVERBOUGHT and ctx.close < ctx.ema_50:
            out.append(
                Signal(
                    code="overbought_in_downtrend",
                    label="Overbought within a downtrend",
                    detail="RSI(14) above 70 while price stays below EMA50.",
                    direction="down",
                )
            )

    # --- moving-average crossovers (SMA20 vs SMA50) ---
    if ctx.sma_cross_up:
        out.append(
            Signal(
                code="sma_bullish_cross",
                label="SMA20 crossed above SMA50",
                detail="The 20-period SMA crossed above the 50-period SMA.",
                direction="up",
            )
        )
    if ctx.sma_cross_down:
        out.append(
            Signal(
                code="sma_bearish_cross",
                label="SMA20 crossed below SMA50",
                detail="The 20-period SMA crossed below the 50-period SMA.",
                direction="down",
            )
        )

    # --- MACD crossovers (MACD vs signal line) ---
    if ctx.macd_cross_up:
        out.append(
            Signal(
                code="macd_bullish_cross",
                label="MACD crossed above signal",
                detail="MACD line crossed above its signal line.",
                direction="up",
            )
        )
    if ctx.macd_cross_down:
        out.append(
            Signal(
                code="macd_bearish_cross",
                label="MACD crossed below signal",
                detail="MACD line crossed below its signal line.",
                direction="down",
            )
        )

    return out
