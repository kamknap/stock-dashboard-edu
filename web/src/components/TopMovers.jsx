const fmtPct = (v) => `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;

function MoverList({ title, items, kind }) {
  return (
    <div>
      <h4 className="mb-1 text-xs uppercase tracking-wide text-slate-400">{title}</h4>
      {items.length === 0 ? (
        <p className="text-sm text-slate-600">—</p>
      ) : (
        <ul className="space-y-1">
          {items.map((m) => (
            <li key={m.symbol} className="flex justify-between text-sm">
              <span className="text-slate-200">{m.symbol}</span>
              <span className={kind === "gain" ? "text-emerald-400" : "text-red-400"}>
                {fmtPct(m.change_pct)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Window({ title, win }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
      <h3 className="mb-3 font-medium">{title}</h3>
      <div className="grid grid-cols-2 gap-4">
        <MoverList title="Gainers" items={win.gainers} kind="gain" />
        <MoverList title="Losers" items={win.losers} kind="loss" />
      </div>
    </div>
  );
}

export default function TopMovers({ movers }) {
  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold">Top movers</h2>
      <div className="grid gap-4 md:grid-cols-2">
        <Window title="Daily" win={movers.daily} />
        <Window title="Weekly" win={movers.weekly} />
      </div>
    </section>
  );
}
