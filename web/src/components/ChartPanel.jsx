import { useState } from "react";
import PriceChart from "./PriceChart";

export default function ChartPanel({ tickers }) {
  const [selected, setSelected] = useState(tickers[0]?.symbol);
  if (!tickers.length) return null;

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">Price chart</h2>
        <select
          value={selected}
          onChange={(e) => setSelected(e.target.value)}
          className="rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-sm text-slate-200"
        >
          {tickers.map((t) => (
            <option key={t.symbol} value={t.symbol}>
              {t.symbol} — {t.name}
            </option>
          ))}
        </select>
      </div>
      <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
        {selected && <PriceChart symbol={selected} />}
      </div>
    </section>
  );
}
