import { useEffect, useState } from "react";
import PriceChart from "./PriceChart";

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
  const [i, setI] = useState(0);
  const [paused, setPaused] = useState(false);
  const n = tickers.length;

  useEffect(() => {
    if (paused || n <= 1) return undefined;
    const id = setInterval(() => setI((p) => (p + 1) % n), 6000);
    return () => clearInterval(id);
  }, [paused, n]);

  if (n === 0) return null;
  const t = tickers[i];
  const prev = () => setI((p) => (p - 1 + n) % n);
  const next = () => setI((p) => (p + 1) % n);
  const rsi = t.indicators?.rsi_14;

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
          <span className="text-xs tabular-nums">{i + 1}/{n}</span>
          <button onClick={next} aria-label="Next" className="px-2 text-lg leading-none hover:text-ink">
            ›
          </button>
        </div>
      </div>

      <div className="flex flex-col p-4">
        <div className="flex items-baseline justify-between gap-3">
          <div className="min-w-0">
            <div className="font-serif text-2xl leading-tight">{t.symbol}</div>
            <div className="truncate text-xs text-inksoft">{t.name}</div>
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
        {tickers.map((tk, k) => (
          <button
            key={tk.symbol}
            onClick={() => setI(k)}
            aria-label={`Show ${tk.symbol}`}
            className={`h-1.5 w-1.5 rounded-full ${k === i ? "bg-ink" : "bg-line"}`}
          />
        ))}
      </div>
    </div>
  );
}
