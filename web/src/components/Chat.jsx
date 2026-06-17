import { useState } from "react";
import { sendChat } from "../lib/api";

export default function Chat() {
  const [messages, setMessages] = useState([]); // { role: "user" | "model", content }
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sources, setSources] = useState([]);

  async function onSend(e) {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;
    const next = [...messages, { role: "user", content: text }];
    setMessages(next);
    setInput("");
    setLoading(true);
    setSources([]);
    try {
      const res = await sendChat(next);
      setMessages([...next, { role: "model", content: res.reply }]);
      setSources(res.sources || []);
    } catch (err) {
      setMessages([...next, { role: "model", content: `Error: ${err.message || err}` }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold">Ask the analyst</h2>
      <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
        <div className="mb-3 max-h-96 space-y-3 overflow-y-auto">
          {messages.length === 0 && (
            <p className="text-sm text-slate-500">
              Name a company or ticker (e.g. “How is NVDA doing?”). You’ll get
              context and risks — never a buy/sell verdict.
            </p>
          )}
          {messages.map((m, i) => (
            <div
              key={i}
              className={m.role === "user" ? "text-right" : "text-left"}
            >
              <span
                className={`inline-block max-w-[85%] whitespace-pre-wrap rounded-lg px-3 py-2 text-sm ${
                  m.role === "user"
                    ? "bg-sky-600/30 text-sky-100"
                    : "bg-slate-800 text-slate-200"
                }`}
              >
                {m.content}
              </span>
            </div>
          ))}
          {loading && <p className="text-sm text-slate-500">Thinking…</p>}
        </div>

        {sources.length > 0 && (
          <div className="mb-3 text-xs text-slate-500">
            Sources:{" "}
            {sources.map((s, i) => (
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

        <form onSubmit={onSend} className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about a watchlist company…"
            className="flex-1 rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-600 focus:border-sky-600 focus:outline-none"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="rounded-md bg-sky-600 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            Send
          </button>
        </form>
      </div>
    </section>
  );
}
