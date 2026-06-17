import { useEffect, useState } from "react";
import { API_BASE, getLatestReport } from "./lib/api";
import Masthead from "./components/Masthead";
import Disclaimer from "./components/Disclaimer";
import TickerCarousel from "./components/TickerCarousel";
import TopMovers from "./components/TopMovers";
import Narrative from "./components/Narrative";
import ChatPanel from "./components/ChatPanel";

export default function App() {
  const [report, setReport] = useState(null);
  const [status, setStatus] = useState("loading"); // loading | ok | empty | error
  const [error, setError] = useState("");
  const [chatOpen, setChatOpen] = useState(false);

  useEffect(() => {
    let active = true;
    getLatestReport()
      .then((data) => {
        if (!active) return;
        if (data === null) setStatus("empty");
        else {
          setReport(data);
          setStatus("ok");
        }
      })
      .catch((e) => {
        if (active) {
          setError(String(e.message || e));
          setStatus("error");
        }
      });
    return () => {
      active = false;
    };
  }, []);

  const notes = report
    ? Object.fromEntries((report.narrative?.ticker_notes || []).map((n) => [n.symbol, n.note]))
    : {};

  return (
    <div className="flex min-h-screen flex-col lg:h-screen lg:overflow-hidden">
      <Masthead report={report} />
      <Disclaimer />

      <main className="mx-auto w-full max-w-screen-2xl flex-1 px-3 py-3 lg:min-h-0">
        {status === "loading" && <p className="text-inksoft">Loading latest report…</p>}
        {status === "empty" && (
          <div className="rounded border border-line bg-panel p-6 text-ink">
            No report yet. Reports are generated at 09:00 and 15:00 (Europe/Warsaw).
          </div>
        )}
        {status === "error" && (
          <div className="rounded border border-down/40 bg-down/5 p-6 text-down">
            Couldn’t load the report: {error}. Is the API running at <code>{API_BASE}</code>?
          </div>
        )}

        {status === "ok" && report && (
          <div className="grid grid-cols-1 gap-3 lg:h-full lg:grid-cols-12">
            <section className="flex flex-col gap-3 lg:col-span-5 lg:min-h-0 lg:overflow-y-auto">
              <TickerCarousel tickers={report.tickers} notes={notes} />
              <TopMovers movers={report.top_movers} />
            </section>

            <section className="lg:col-span-4 lg:min-h-0">
              <div className="h-full rounded border border-line bg-panel p-4 lg:overflow-hidden">
                <Narrative narrative={report.narrative} sources={report.sources} />
              </div>
            </section>

            <aside className="hidden rounded border border-line lg:col-span-3 lg:block lg:min-h-0">
              <ChatPanel />
            </aside>
          </div>
        )}
      </main>

      {/* Mobile: floating button + chat drawer */}
      <button
        onClick={() => setChatOpen(true)}
        className="fixed bottom-4 right-4 z-30 rounded-full bg-ink px-4 py-3 text-sm text-paper shadow-lg lg:hidden"
      >
        Ask the analyst
      </button>
      {chatOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-black/30" onClick={() => setChatOpen(false)} />
          <div className="absolute inset-y-0 right-0 w-full max-w-sm border-l border-line bg-panel">
            <ChatPanel onClose={() => setChatOpen(false)} />
          </div>
        </div>
      )}
    </div>
  );
}
