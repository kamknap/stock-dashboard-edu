import { useEffect } from "react";

function fmtUpdated(iso) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const date = d.toLocaleDateString("en-GB", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
  const time = d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
  return `${date} · updated ${time}`;
}

function paragraphs(body) {
  return String(body || "")
    .split(/\n{2,}|\n/)
    .map((p) => p.trim())
    .filter(Boolean);
}

// The "Daily Brief" reading modal: long-form, AI-generated world context. The
// content is read straight off report.daily_brief (cached server-side once per
// run) so opening it never calls the model. Centered card on desktop, bottom
// sheet on mobile. Closes on x / backdrop / Esc; locks body scroll while open.
export default function DailyBriefModal({ brief, onClose }) {
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [onClose]);

  const sections = brief?.sections || [];
  const watch = brief?.watch || [];
  const sources = brief?.sources || [];

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center lg:items-center">
      <div className="absolute inset-0 bg-[rgba(20,18,14,0.5)]" onClick={onClose} />

      <div className="relative flex max-h-[88vh] w-full flex-col overflow-hidden rounded-t-[18px] border-t-2 border-ink bg-paper shadow-[0_-8px_24px_rgba(0,0,0,.2)] lg:max-w-[740px] lg:rounded lg:border-2 lg:shadow-[0_24px_70px_rgba(0,0,0,.32)]">
        <div className="sticky top-0 flex items-start justify-between gap-4 border-b border-line bg-paper px-6 py-4">
          <div className="min-w-0">
            <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-gold">
              ✦ Daily Brief · AI-generated
            </p>
            {brief?.updated_at && (
              <p className="mt-0.5 text-xs text-inksoft">{fmtUpdated(brief.updated_at)}</p>
            )}
          </div>
          <button
            onClick={onClose}
            aria-label="Close"
            className="flex h-[34px] w-[34px] shrink-0 items-center justify-center rounded-full border border-line text-inksoft hover:text-ink"
          >
            ✕
          </button>
        </div>

        <div className="overflow-y-auto px-6 py-5">
          {!brief ? (
            <div className="py-10 text-center">
              <h2 className="font-serif text-2xl font-bold text-ink">Brief not ready yet</h2>
              <p className="mt-2 text-sm text-inksoft">
                The Daily Brief is generated with each report (09:00 and 15:00, Europe/Warsaw).
                Check back after the next run.
              </p>
            </div>
          ) : (
            <>
              <h2 className="font-serif text-[28px] font-extrabold leading-tight tracking-tight text-ink lg:text-[34px]">
                {brief.title}
              </h2>
              {brief.lede && (
                <p className="mt-3 text-[17px] leading-relaxed text-ink">{brief.lede}</p>
              )}

              {sections.map((s, i) => (
                <section key={i} className="mt-7">
                  <h3 className="border-b border-line pb-2 text-[11px] font-bold uppercase tracking-[0.12em] text-up">
                    {s.heading}
                  </h3>
                  {paragraphs(s.body).map((p, j) => (
                    <p key={j} className="mt-2 text-[15px] leading-relaxed text-ink">
                      {p}
                    </p>
                  ))}
                </section>
              ))}

              {brief.pull_quote && (
                <blockquote className="mt-7 border-l-[3px] border-gold pl-[18px] font-serif text-[18px] italic text-ink">
                  {brief.pull_quote}
                </blockquote>
              )}

              {watch.length > 0 && (
                <div className="mt-7 rounded border border-line bg-panel p-5">
                  <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-gold">
                    What to watch this week
                  </p>
                  <ul className="mt-2 list-disc space-y-1 pl-4 text-sm leading-snug text-ink">
                    {watch.map((w, i) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="mt-7 flex flex-wrap items-center gap-3 border-t border-line pt-4 text-[12px] text-inksoft">
                <span className="rounded-full bg-gold/10 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-gold">
                  AI-generated · educational
                </span>
                {sources.length > 0 && (
                  <details>
                    <summary className="cursor-pointer list-none">
                      Synthesised from {sources.length} cited source
                      {sources.length === 1 ? "" : "s"}
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
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
