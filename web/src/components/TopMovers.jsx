const fmtPct = (v) => `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;

function MoverRow({ m, kind }) {
  return (
    <li className="flex items-baseline justify-between gap-2">
      <span className="truncate text-ink">{m.symbol}</span>
      <span className={`tabular-nums ${kind === "gain" ? "text-up" : "text-down"}`}>
        {fmtPct(m.change_pct)}
      </span>
    </li>
  );
}

function Window({ title, win }) {
  return (
    <div>
      <h3 className="mb-1 border-b border-line pb-1 text-[11px] uppercase tracking-widest text-inksoft">
        {title}
      </h3>
      <ul className="space-y-0.5">
        {win.gainers.slice(0, 3).map((m) => (
          <MoverRow key={`g-${m.symbol}`} m={m} kind="gain" />
        ))}
        {win.losers.slice(0, 3).map((m) => (
          <MoverRow key={`l-${m.symbol}`} m={m} kind="loss" />
        ))}
      </ul>
    </div>
  );
}

export default function TopMovers({ movers }) {
  return (
    <div className="rounded border border-line bg-panel p-3">
      <h2 className="mb-2 text-base">Top movers</h2>
      <div className="grid grid-cols-2 gap-4 text-sm">
        <Window title="Daily" win={movers.daily} />
        <Window title="Weekly" win={movers.weekly} />
      </div>
    </div>
  );
}
