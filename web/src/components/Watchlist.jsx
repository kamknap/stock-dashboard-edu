import { useMemo, useState } from "react";
import PriceChart from "./PriceChart";
import Sparkline from "./Sparkline";
import { getAnalysis } from "../lib/api";

const fmt = (n) =>
  n == null ? "n/a" : Number(n).toLocaleString(undefined, { maximumFractionDigits: 2 });

function Change({ value }) {
  if (value == null) return <span className="text-inksoft">n/a</span>;
  const up = value >= 0;
  return (
    <span className={`font-semibold tabular-nums ${up ? "text-up" : "text-down"}`}>
      {up ? "+" : ""}
      {value.toFixed(2)}%
    </span>
  );
}

// Static watchlist: one row per ticker, no auto-rotation. A row expands to
// reveal its full chart; search appends any ticker to the list.
export default function Watchlist({ tickers, notes }) {
  const [extra, setExtra] = useState([]); // user-searched tickers
  const [expanded, setExpanded] = useState(null); // symbol | null
  const [showAll, setShowAll] = useState(false); // mobile: top-3 vs full
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState("");

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

  // The single most notable name (largest absolute move) gets a soft highlight.
  const notable = useMemo(() => {
    let best = null;
    let bestAbs = -1;
    for (const t of items) {
      const c = t.snapshot?.change_pct;
      if (c != null && Math.abs(c) > bestAbs) {
        bestAbs = Math.abs(c);
        best = t.symbol;
      }
    }
    return best;
  }, [items]);

  async function onSearch(e) {
    e.preventDefault();
    const sym = query.trim().toUpperCase();
    if (!sym || searching) return;
    setSearchError("");
    const existing = items.find((x) => x.symbol === sym);
    if (existing) {
      setExpanded(sym);
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
        setExpanded(sym);
        setShowAll(true);
        setQuery("");
      }
    } catch {
      setSearchError("Lookup failed.");
    } finally {
      setSearching(false);
    }
  }

  return (
    <div className="min-w-0">
      <header>
        <h2 className="text-[11px] font-bold uppercase tracking-[0.12em] text-inksoft">
          Market at a glance
        </h2>
        <p className="mt-0.5 text-xs text-inksoft">Tap a row to expand its chart.</p>
      </header>

      <div className="mt-3">
        {items.map((t, i) => {
          const isNotable = t.symbol === notable;
          const isExpanded = expanded === t.symbol;
          const hideOnMobile = i >= 3 && !showAll;
          const up = (t.snapshot?.change_pct ?? 0) >= 0;
          return (
            <div key={t.symbol} className={hideOnMobile ? "hidden lg:block" : ""}>
              <button
                onClick={() => setExpanded(isExpanded ? null : t.symbol)}
                className={`flex w-full min-w-0 items-center gap-3.5 border-b border-line py-3 text-left ${
                  isNotable ? "bg-beige/40 lg:-mx-7 lg:px-7" : ""
                }`}
              >
                <div className="min-w-0 flex-1">
                  <div className="text-[15px] font-bold text-ink">{t.symbol}</div>
                  <div className="truncate text-xs text-inksoft">
                    {notes[t.symbol] || t.name || ""}
                  </div>
                </div>
                <Sparkline symbol={t.symbol} up={up} width={72} height={22} />
                <div className="min-w-[96px] text-right">
                  <div className="text-[15px] font-semibold tabular-nums text-ink">
                    {fmt(t.snapshot?.price)}{" "}
                    <span className="text-xs font-normal text-inksoft">{t.currency}</span>
                  </div>
                  <div className="text-[13px]">
                    <Change value={t.snapshot?.change_pct} />
                  </div>
                </div>
              </button>
              {isExpanded && (
                <div className="border-b border-line py-3">
                  <PriceChart symbol={t.symbol} height={200} />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {items.length > 3 && (
        <button
          onClick={() => setShowAll((v) => !v)}
          className="mt-2 text-xs font-semibold uppercase tracking-widest text-inksoft hover:text-ink lg:hidden"
        >
          {showAll ? "Show fewer" : `Show all ${items.length}`}
        </button>
      )}

      <form onSubmit={onSearch} className="mt-3 flex items-center gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search any ticker (e.g. TSLA, KGH.WA)"
          className="min-w-0 flex-1 rounded border border-line bg-paper px-3 py-2 text-sm text-ink placeholder:text-inksoft/70 focus:border-ink focus:outline-none"
        />
        <button
          type="submit"
          disabled={searching || !query.trim()}
          className="rounded bg-ink px-3 py-2 text-sm text-paper disabled:opacity-40"
        >
          {searching ? "..." : "Go"}
        </button>
      </form>
      {searchError && <p className="mt-1 text-xs text-down">{searchError}</p>}
    </div>
  );
}
