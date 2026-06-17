// Client-side indicator overlays for the chart. These mirror the backend's
// definitions (SMA = rolling mean, EMA = recursive with adjust=False) so the
// chart matches the report numbers. The backend remains the source of truth.

export function sma(values, period) {
  return values.map((_, i) => {
    if (i < period - 1) return null;
    let sum = 0;
    for (let j = i - period + 1; j <= i; j += 1) sum += values[j];
    return sum / period;
  });
}

export function ema(values, period) {
  const k = 2 / (period + 1);
  let prev;
  return values.map((v, i) => {
    prev = i === 0 ? v : v * k + prev * (1 - k);
    return prev;
  });
}
