const BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8080";

export const API_BASE = BASE;

/** Fetch the latest stored daily report, or null if none exists yet (404). */
export async function getLatestReport() {
  const res = await fetch(`${BASE}/reports/latest`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/** Fetch the daily OHLCV candle series for a watchlist symbol. */
export async function getCandles(symbol, range = "6mo", interval = "1d") {
  const url = `${BASE}/market/${encodeURIComponent(symbol)}/candles?range=${range}&interval=${interval}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/** Send the conversation history to the analytical chat agent. */
export async function sendChat(messages) {
  const res = await fetch(`${BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
