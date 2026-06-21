import { useEffect, useMemo, useState } from "react";
import PriceChart from "./PriceChart";
import { getAnalysis } from "../lib/api";

const fmt = (n) =>
  n == null ? "n/a" : Number(n).toLocaleString(undefined, { maximumFractionDigits: 2 });

function Change({ value }) {
  if (value == null) return <span className="text-inksoft">n/a</span>;
  const up = value >= 0;
  return (
    <span className={`tabular-nums ${up ? "text-up" : "text-down"}`}>
      {up ? "+" : ""}
      {value.toFixed(2)}%
    </span>
  );
}

function SignalChip({ signal }) {
  const tone =
    signal.direction === "up"
      ? "bg-up/10 text-up"
      : signal.direction === "down"
        ? "bg-down/10 text-down"
        : "bg-beige text-inksoft";
  return (
    <span className={`rounded px-1.5 py-0.5 text-[11px] ${tone}`} title={signal.detail}>
      {signal.label}
    </span>
  );
}

export default function TickerCarousel({ tickers, notes }) {
  const [extra, setExtra] = useState([]); // user-searched tickers
  const items = useMemo(() => {
    const seen = new Set();
    const out = [];
    for (const t of [...tickers, ...extra]) {
      if (t && !seen.has(t.symbol)) {
        seen.add(t.symbol);
        out.push(t);
      }
    }
    return out;
  }, [tickers, extra]);

  const n = items.length;
  // Start on a random watchlist ticker so it isn't always the same one first.
  const [i, setI] = useState(() => (tickers.length ? Math.floor(Math.random() * tickers.length) : 0));
  const [paused, setPaused] = useState(false);
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState("");

  useEffect(() => {
    if (paused || n <= 1) return undefined;
    const id = setInterval(() => setI((p) => (p + 1) % n), 6000);
    return () => clearInterval(id);
  }, [paused, n]);

  if (n === 0) return null;
  const idx = Math.min(i, n - 1);
  const t = items[idx];
  const prev = () => setI((idx - 1 + n) % n);
  const next = () => setI((idx + 1) % n);
  const rsi = t.indicators?.rsi_14;

  async function onSearch(e) {
    e.preventDefault();
    const sym = query.trim().toUpperCase();
    if (!sym || searching) return;
    setSearchError("");
    const existing = items.findIndex((x) => x.symbol === sym);
    if (existing >= 0) {
      setI(existing);
      setQuery("");
      return;
    }
    setSearching(true);
    try {
      const a = await getAnalysis(sym);
      if (!a) {
        setSearchError(`Not found: ${sym}`);
      } else {
        setExtra((prev) => [...prev, a]);
        setI(n); // appended item becomes the new last index
        setQuery("");
      }
    } catch {
      setSearchError("Lookup failed.");
    } finally {
      setSearching(false);
    }
  }

  return (
    <div
      className="flex flex-col rounded border border-line bg-panel"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
    >
      <div className="flex items-center justify-between border-b border-line px-3 py-2">
        <h2 className="text-base">Watchlist</h2>
        <div className="flex items-center gap-2 text-inksoft">
          <button onClick={prev} aria-label="Previous" className="px-2 text-lg leading-none hover:text-ink">
            ‹
          </button>
          <span className="text-xs tabular-nums">{idx + 1}/{n}</span>
          <button onClick={next} aria-label="Next" className="px-2 text-lg leading-none hover:text-ink">
            ›
          </button>
        </div>
      </div>

      <form onSubmit={onSearch} className="flex items-center gap-2 border-b border-line px-3 py-1.5">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setPaused(true)}
          onBlur={() => setPaused(false)}
          placeholder="Search any ticker (e.g. TSLA, KGH.WA)"
          className="flex-1 rounded border border-line bg-paper px-2 py-1 text-xs text-ink placeholder:text-inksoft/70 focus:border-ink focus:outline-none"
        />
        <button
          type="submit"
          disabled={searching || !query.trim()}
          className="rounded bg-ink px-2.5 py-1 text-xs text-paper disabled:opacity-40"
        >
          {searching ? "…" : "Go"}
        </button>
      </form>
      {searchError && <p className="px-3 pt-1 text-xs text-down">{searchError}</p>}

      <div className="flex flex-col p-4">
        <div className="flex items-baseline justify-between gap-3">
          <div className="min-w-0">
            <div className="font-serif text-2xl leading-tight">{t.symbol}</div>
            <div className="truncate text-xs text-inksoft">{t.name || ""}</div>
          </div>
          <div className="text-right">
            <div className="text-xl tabular-nums">
              {fmt(t.snapshot?.price)} <span className="text-xs text-inksoft">{t.currency}</span>
            </div>
            <Change value={t.snapshot?.change_pct} />
          </div>
        </div>

        <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-inksoft">
          <span>RSI14 {rsi == null ? "n/a" : rsi.toFixed(1)}</span>
          {t.signals.map((s) => (
            <SignalChip key={s.code} signal={s} />
          ))}
        </div>

        {notes[t.symbol] && (
          <p className="mt-2 line-clamp-2 text-sm text-inksoft">{notes[t.symbol]}</p>
        )}

        <div className="mt-3">
          <PriceChart symbol={t.symbol} height={200} />
        </div>
      </div>

      <div className="flex flex-wrap justify-center gap-1.5 pb-2">
        {items.map((tk, k) => (
          <button
            key={tk.symbol}
            onClick={() => setI(k)}
            aria-label={`Show ${tk.symbol}`}
            className={`h-1.5 w-1.5 rounded-full ${k === idx ? "bg-ink" : "bg-line"}`}
          />
        ))}
      </div>
    </div>
  );
}
