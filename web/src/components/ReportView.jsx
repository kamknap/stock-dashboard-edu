const fmt = (n) =>
  n == null ? "—" : Number(n).toLocaleString(undefined, { maximumFractionDigits: 2 });

function Change({ value }) {
  if (value == null) return <span className="text-slate-400">—</span>;
  const up = value >= 0;
  return (
    <span className={up ? "text-emerald-400" : "text-red-400"}>
      {up ? "+" : ""}
      {value.toFixed(2)}%
    </span>
  );
}

function SignalChip({ signal }) {
  const tone =
    signal.direction === "up"
      ? "bg-emerald-500/15 text-emerald-300"
      : signal.direction === "down"
        ? "bg-red-500/15 text-red-300"
        : "bg-slate-700 text-slate-300";
  return (
    <span className={`rounded px-1.5 py-0.5 text-xs ${tone}`} title={signal.detail}>
      {signal.label}
    </span>
  );
}

export default function ReportView({ report }) {
  const notes = Object.fromEntries(
    (report.narrative?.ticker_notes || []).map((n) => [n.symbol, n.note]),
  );
  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">
          Daily report — {report.date} · {report.session}
        </h2>
        <span
          className={`rounded-full px-2 py-1 text-xs ${
            report.llm_ok
              ? "bg-emerald-500/15 text-emerald-300"
              : "bg-amber-500/15 text-amber-300"
          }`}
        >
          {report.llm_ok ? "live news grounding" : "fallback (no live news)"}
        </span>
      </div>

      <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
        <h3 className="mb-2 text-sm uppercase tracking-wide text-slate-400">
          Market context
        </h3>
        <p className="leading-relaxed text-slate-200">
          {report.narrative?.market_summary}
        </p>
      </div>

      <div className="overflow-hidden rounded-lg border border-slate-800 bg-slate-900">
        <table className="w-full text-sm">
          <thead className="bg-slate-800/50 text-slate-400">
            <tr>
              <th className="px-4 py-2 text-left">Ticker</th>
              <th className="px-4 py-2 text-right">Price</th>
              <th className="px-4 py-2 text-right">Daily</th>
              <th className="px-4 py-2 text-right">RSI14</th>
              <th className="px-4 py-2 text-left">Signals</th>
            </tr>
          </thead>
          <tbody>
            {report.tickers.map((t) => (
              <tr key={t.symbol} className="border-t border-slate-800 align-top">
                <td className="px-4 py-2">
                  <div className="font-medium">{t.symbol}</div>
                  <div className="text-xs text-slate-500">{t.name}</div>
                  {notes[t.symbol] && (
                    <div className="mt-1 max-w-md text-xs text-slate-400">
                      {notes[t.symbol]}
                    </div>
                  )}
                </td>
                <td className="px-4 py-2 text-right">
                  {fmt(t.snapshot?.price)}{" "}
                  <span className="text-xs text-slate-500">{t.currency}</span>
                </td>
                <td className="px-4 py-2 text-right">
                  <Change value={t.snapshot?.change_pct} />
                </td>
                <td className="px-4 py-2 text-right">
                  {t.indicators?.rsi_14 == null ? "—" : t.indicators.rsi_14.toFixed(1)}
                </td>
                <td className="px-4 py-2">
                  <div className="flex flex-wrap gap-1">
                    {t.signals.map((s) => (
                      <SignalChip key={s.code} signal={s} />
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {report.narrative?.risks?.length > 0 && (
        <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
          <h3 className="mb-2 text-sm uppercase tracking-wide text-slate-400">Risks</h3>
          <ul className="list-inside list-disc space-y-1 text-slate-300">
            {report.narrative.risks.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </div>
      )}

      {report.sources?.length > 0 && (
        <div className="text-xs text-slate-500">
          Sources:{" "}
          {report.sources.map((s, i) => (
            <a
              key={i}
              href={s.url}
              target="_blank"
              rel="noreferrer"
              className="mr-2 underline hover:text-slate-300"
            >
              {s.title || s.url}
            </a>
          ))}
        </div>
      )}
    </section>
  );
}
