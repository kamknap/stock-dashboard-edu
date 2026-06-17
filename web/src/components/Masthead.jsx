export default function Masthead({ report }) {
  const today = new Date().toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });
  return (
    <header className="border-b-2 border-ink bg-paper">
      <div className="mx-auto grid max-w-screen-2xl grid-cols-3 items-center px-4 py-1.5 text-[11px] uppercase tracking-widest text-inksoft">
        <span className="justify-self-start">{today}</span>
        <span className="hidden justify-self-center text-center sm:block">
          Educational market analysis
        </span>
        {report ? (
          <span
            className={`justify-self-end text-right ${report.llm_ok ? "text-up" : "text-gold"}`}
          >
            {report.date} · {report.session} · {report.llm_ok ? "live grounding" : "fallback"}
          </span>
        ) : (
          <span className="justify-self-end" />
        )}
      </div>
      <div className="border-t border-line py-1.5 text-center">
        <h1 className="text-3xl font-black tracking-tight sm:text-4xl">Stock Dashboard</h1>
      </div>
    </header>
  );
}
