import { useEffect, useState } from "react";
import { API_BASE, getLatestReport } from "./lib/api";
import Disclaimer from "./components/Disclaimer";
import ReportView from "./components/ReportView";
import TopMovers from "./components/TopMovers";
import ChartPanel from "./components/ChartPanel";
import Chat from "./components/Chat";

export default function App() {
  const [report, setReport] = useState(null);
  const [status, setStatus] = useState("loading"); // loading | ok | empty | error
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    getLatestReport()
      .then((data) => {
        if (!active) return;
        if (data === null) {
          setStatus("empty");
        } else {
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

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 px-6 py-4">
        <h1 className="text-xl font-semibold">
          Stock Dashboard{" "}
          <span className="font-normal text-slate-400">(educational)</span>
        </h1>
      </header>
      <Disclaimer />
      <main className="mx-auto max-w-5xl space-y-8 px-6 py-6">
        {status === "loading" && (
          <p className="text-slate-400">Loading latest report…</p>
        )}
        {status === "empty" && (
          <div className="rounded-lg border border-slate-800 bg-slate-900 p-6 text-slate-300">
            No report yet. Reports are generated at 09:00 and 15:00 (Europe/Warsaw).
          </div>
        )}
        {status === "error" && (
          <div className="rounded-lg border border-red-900 bg-red-950 p-6 text-red-200">
            Couldn’t load the report: {error}. Is the API running at{" "}
            <code>{API_BASE}</code>?
          </div>
        )}
        {status === "ok" && report && (
          <>
            <ReportView report={report} />
            <TopMovers movers={report.top_movers} />
            <ChartPanel tickers={report.tickers} />
          </>
        )}
        <Chat />
      </main>
    </div>
  );
}
