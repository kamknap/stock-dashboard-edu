import { useEffect, useState } from "react";
import { API_BASE, getLatestReport } from "./lib/api";
import Masthead from "./components/Masthead";
import Disclaimer from "./components/Disclaimer";
import Watchlist from "./components/Watchlist";
import TopMovers from "./components/TopMovers";
import Narrative from "./components/Narrative";
import ChatPanel from "./components/ChatPanel";

function Centered({ children }) {
  return <div className="mx-auto max-w-xl px-6 py-20 text-center">{children}</div>;
}

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
    <div className="flex min-h-screen flex-col">
      <Masthead report={report} onAskAnalyst={() => setChatOpen(true)} />
      <Disclaimer />

      <main className="mx-auto w-full max-w-screen-2xl flex-1 pb-24 lg:pb-0">
        {status === "loading" && (
          <Centered>
            <p className="text-inksoft">Loading the latest brief…</p>
          </Centered>
        )}
        {status === "empty" && (
          <Centered>
            <h2 className="font-serif text-2xl font-bold text-ink">No brief yet</h2>
            <p className="mt-2 text-sm text-inksoft">
              Reports are generated at 09:00 and 15:00 (Europe/Warsaw). Check back shortly.
            </p>
          </Centered>
        )}
        {status === "error" && (
          <Centered>
            <h2 className="font-serif text-2xl font-bold text-down">Could not load the brief</h2>
            <p className="mt-2 text-sm text-inksoft">
              {error}. Is the API running at <code>{API_BASE}</code>?
            </p>
          </Centered>
        )}

        {status === "ok" && report && (
          <div className="grid grid-cols-1 lg:grid-cols-[1.35fr_1fr]">
            <section className="min-w-0 border-b border-line px-5 py-6 lg:border-b-0 lg:border-r lg:p-9">
              <Narrative report={report} />
            </section>
            <section className="flex min-w-0 flex-col gap-5 px-5 py-6 lg:p-7">
              <Watchlist tickers={report.tickers} notes={notes} />
              <TopMovers movers={report.top_movers} />
            </section>
          </div>
        )}
      </main>

      {/* Mobile: sticky "Ask the analyst" bar with a fade so content scrolls under it. */}
      {status === "ok" && (
        <div className="fixed inset-x-0 bottom-0 z-30 bg-gradient-to-t from-paper via-paper/95 to-transparent px-4 pb-3 pt-8 lg:hidden">
          <button
            onClick={() => setChatOpen(true)}
            className="w-full rounded-full bg-ink py-3 text-sm font-semibold text-paper shadow-[0_6px_20px_rgba(0,0,0,.18)]"
          >
            Ask the analyst
          </button>
        </div>
      )}

      {/* Chat: right-side panel on desktop, full-width bottom sheet on mobile. */}
      {chatOpen && (
        <div className="fixed inset-0 z-40">
          <div className="absolute inset-0 bg-black/30" onClick={() => setChatOpen(false)} />
          <div className="absolute inset-x-0 bottom-0 h-[85vh] overflow-hidden rounded-t-[18px] border-t-2 border-ink bg-panel shadow-[0_-8px_24px_rgba(0,0,0,.12)] lg:inset-y-0 lg:left-auto lg:right-0 lg:h-auto lg:w-full lg:max-w-md lg:rounded-none lg:border-l-2 lg:border-t-0 lg:shadow-[-8px_0_24px_rgba(0,0,0,.12)]">
            <ChatPanel onClose={() => setChatOpen(false)} />
          </div>
        </div>
      )}
    </div>
  );
}
