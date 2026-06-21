// The "brief" -- the editorial hero of the Quiet Board. It leads with a
// headline + lede, then three numbered "what matters today" points, then
// Opportunities / Risks, and finally a collapsible sources footer.
//
// headline + highlights come from the LLM narrative when present; if a stored
// report predates those fields, we derive sensible fallbacks from the
// deterministic data (market_summary + top movers), so the page always reads
// well. The numbers themselves stay the backend's source of truth.

const fmtPct = (v) => (v == null ? "n/a" : `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`);

function withBoldNumbers(text) {
  // Bold figures (12.3, +1.5%, 38) so key data pops in the prose.
  return text.split(/([-+]?\d[\d.,]*%?)/g).map((part, i) =>
    /^[-+]?\d/.test(part) ? (
      <strong key={i} className="font-semibold text-ink">
        {part}
      </strong>
    ) : (
      part
    ),
  );
}

function eyebrowText(report) {
  const label = report.session === "morning" ? "Morning Brief" : "Afternoon Brief";
  let day = "";
  if (report.date) {
    const d = new Date(`${report.date}T00:00:00`);
    if (!Number.isNaN(d.getTime())) {
      day = d.toLocaleDateString("en-GB", { day: "numeric", month: "long" });
    }
  }
  return day ? `${label} · ${day}` : label;
}

function deriveHeadline(narrative) {
  if (narrative?.headline) return narrative.headline;
  const summary = narrative?.market_summary || "";
  const first = summary.split(/(?<=[.!?])\s/)[0] || summary;
  return first.replace(/\.$/, "") || "Today's market brief";
}

function deriveHighlights(report) {
  const given = report.narrative?.highlights || [];
  if (given.length) return given.slice(0, 3);

  const out = [];
  const tickers = report.tickers || [];
  const n = tickers.length;
  const above = tickers.filter(
    (t) =>
      t.indicators?.close != null &&
      t.indicators?.ema_50 != null &&
      t.indicators.close > t.indicators.ema_50,
  ).length;
  if (n) out.push(`${above} of ${n} watchlist names closed above their EMA50.`);

  const dg = report.top_movers?.daily?.gainers?.[0];
  if (dg) out.push(`${dg.symbol} led the daily tape at ${fmtPct(dg.change_pct)}.`);
  const dl = report.top_movers?.daily?.losers?.[0];
  if (dl) out.push(`${dl.symbol} lagged at ${fmtPct(dl.change_pct)}.`);

  return out.slice(0, 3);
}

function SectionHeader({ title, accent }) {
  return (
    <h3
      className={`border-b border-line pb-2 text-[11px] font-bold uppercase tracking-[0.12em] ${
        accent || "text-inksoft"
      }`}
    >
      {title}
    </h3>
  );
}

export default function Narrative({ report }) {
  const narrative = report.narrative || {};
  const sources = report.sources || [];
  const headline = deriveHeadline(narrative);
  const highlights = deriveHighlights(report);
  const opportunities = narrative.opportunities || [];
  const risks = narrative.risks || [];

  return (
    <article className="flex min-w-0 flex-col">
      <p className="text-[12px] font-bold uppercase tracking-[0.12em] text-gold">
        {eyebrowText(report)}
      </p>

      <h2 className="mt-3 text-balance font-serif text-[26px] font-extrabold leading-[1.1] tracking-tight text-ink lg:text-[36px]">
        {headline}
      </h2>

      {narrative.market_summary && (
        <p className="mt-4 text-base leading-relaxed text-ink">
          {narrative.market_summary}
        </p>
      )}

      {highlights.length > 0 && (
        <div className="mt-6">
          <SectionHeader title="What matters today" />
          <ol className="mt-3 flex flex-col gap-2.5">
            {highlights.map((h, i) => (
              <li key={i} className="flex items-baseline gap-2.5">
                <span className="font-serif text-lg font-bold text-gold">{i + 1}</span>
                <span className="text-[15px] leading-snug text-ink">
                  {withBoldNumbers(h)}
                </span>
              </li>
            ))}
          </ol>
        </div>
      )}

      {(opportunities.length > 0 || risks.length > 0) && (
        <div className="mt-7 grid grid-cols-1 gap-6 sm:grid-cols-2">
          <div>
            <SectionHeader title="Opportunities" accent="text-up" />
            <ul className="mt-2 list-disc space-y-1 pl-4 text-sm leading-snug text-ink">
              {opportunities.map((o, i) => (
                <li key={i}>{o}</li>
              ))}
            </ul>
          </div>
          <div>
            <SectionHeader title="Risks" accent="text-gold" />
            <ul className="mt-2 list-disc space-y-1 pl-4 text-sm leading-snug text-ink">
              {risks.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {sources.length > 0 && (
        <details className="mt-7 border-t border-line pt-4 text-[12px] text-inksoft">
          <summary className="cursor-pointer list-none">
            Grounded in {sources.length} cited source{sources.length === 1 ? "" : "s"}
            <span className="ml-1 underline decoration-line">view all</span>
          </summary>
          <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1">
            {sources.map((s, i) => (
              <a
                key={i}
                href={s.url}
                target="_blank"
                rel="noreferrer"
                className="break-words underline decoration-line hover:text-ink"
              >
                {s.title || "source"}
              </a>
            ))}
          </div>
        </details>
      )}
    </article>
  );
}
