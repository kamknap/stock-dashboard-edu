function Section({ title, accent, children }) {
  return (
    <div>
      <h3
        className={`mb-1 border-b pb-1 text-[11px] uppercase tracking-widest ${
          accent || "border-line text-inksoft"
        }`}
      >
        {title}
      </h3>
      {children}
    </div>
  );
}

export default function Narrative({ narrative, sources }) {
  const opportunities = narrative?.opportunities || [];
  const risks = narrative?.risks || [];
  return (
    <div className="flex h-full min-h-0 flex-col gap-4 overflow-y-auto pr-1">
      <Section title="Market context">
        <p className="text-sm leading-relaxed text-ink">{narrative?.market_summary}</p>
      </Section>

      {opportunities.length > 0 && (
        <Section title="Opportunities" accent="border-line text-up">
          <ul className="list-inside list-disc space-y-1 text-sm text-ink/90">
            {opportunities.map((o, i) => (
              <li key={i}>{o}</li>
            ))}
          </ul>
        </Section>
      )}

      {risks.length > 0 && (
        <Section title="Risks" accent="border-line text-gold">
          <ul className="list-inside list-disc space-y-1 text-sm text-ink/90">
            {risks.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </Section>
      )}

      {sources?.length > 0 && (
        <details className="text-xs">
          <summary className="cursor-pointer border-b border-line pb-1 text-[11px] uppercase tracking-widest text-inksoft">
            Sources ({sources.length})
          </summary>
          <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1">
            {sources.map((s, i) => (
              <a
                key={i}
                href={s.url}
                target="_blank"
                rel="noreferrer"
                className="break-words text-inksoft underline decoration-line hover:text-ink"
              >
                {s.title || "source"}
              </a>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}
