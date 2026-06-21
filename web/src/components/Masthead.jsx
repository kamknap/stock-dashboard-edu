export default function Masthead({ report, onAskAnalyst, onOpenBrief }) {
  const today = new Date().toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });
  return (
    <header className="border-b-2 border-ink bg-paper">
      <div className="mx-auto flex max-w-screen-2xl flex-col items-center gap-0.5 px-4 py-1.5 text-[11px] uppercase tracking-widest text-inksoft sm:grid sm:grid-cols-3 sm:items-center sm:gap-0">
        <span className="sm:justify-self-start">{today}</span>
        <span className="hidden sm:block sm:justify-self-center sm:text-center">
          Educational market analysis
        </span>
        {report ? (
          <span
            className={`text-center ${report.llm_ok ? "text-up" : "text-gold"} sm:justify-self-end sm:text-right`}
          >
            {report.date} · {report.session} · {report.llm_ok ? "live grounding" : "fallback"}
          </span>
        ) : (
          <span className="hidden sm:block sm:justify-self-end" />
        )}
      </div>
      <div className="relative border-t border-line py-1.5 text-center">
        <h1 className="text-3xl font-black tracking-tight sm:text-4xl">Stock Dashboard</h1>
        <div className="absolute right-6 top-1/2 hidden -translate-y-1/2 items-center gap-2 lg:flex">
          {onOpenBrief && (
            <button
              onClick={onOpenBrief}
              className="rounded-full bg-ink px-4 py-2 text-[13px] font-semibold text-paper hover:opacity-90"
            >
              ✦ Daily Brief
            </button>
          )}
          {onAskAnalyst && (
            <button
              onClick={onAskAnalyst}
              className="rounded-full border border-ink bg-paper px-4 py-2 text-[13px] font-semibold text-ink hover:bg-ink hover:text-paper"
            >
              Ask the analyst →
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
