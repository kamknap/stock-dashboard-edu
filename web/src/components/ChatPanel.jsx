import { useState } from "react";
import { sendChat } from "../lib/api";

function stripMarkdown(text) {
  return text
    .replace(/\*\*(.*?)\*\*/g, "$1")
    .replace(/__(.*?)__/g, "$1")
    .replace(/`([^`]*)`/g, "$1")
    .replace(/(^|\n)\s*#{1,6}\s*/g, "$1")
    .replace(/(^|\n)\s*[*-]\s+/g, "$1\u2022 ");
}

export default function ChatPanel({ onClose }) {
  const [messages, setMessages] = useState([]);
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
    <div className="flex h-full min-h-0 flex-col bg-panel">
      <div className="flex items-center justify-between border-b border-line px-4 py-2">
        <h2 className="text-lg">Ask the analyst</h2>
        {onClose && (
          <button onClick={onClose} className="px-1 text-inksoft hover:text-ink" aria-label="Close">
            ✕
          </button>
        )}
      </div>

      <div className="flex-1 min-h-0 space-y-3 overflow-y-auto px-4 py-3 text-sm">
        {messages.length === 0 && (
          <p className="text-inksoft">
            Name a company or ticker (e.g. “How is NVDA doing?”). You’ll get context and
            risks, never a buy/sell verdict.
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "text-right" : "text-left"}>
            <span
              className={`inline-block max-w-[88%] whitespace-pre-wrap rounded px-3 py-2 text-left ${
                m.role === "user"
                  ? "bg-beige text-ink"
                  : "border border-line bg-paper text-ink"
              }`}
            >
              {m.role === "model" ? stripMarkdown(m.content) : m.content}
            </span>
          </div>
        ))}
        {loading && <p className="text-inksoft">Thinking…</p>}
        {sources.length > 0 && (
          <div className="text-xs text-inksoft">
            Sources:{" "}
            {sources.map((s, i) => (
              <a
                key={i}
                href={s.url}
                target="_blank"
                rel="noreferrer"
                className="mr-2 break-words underline decoration-line hover:text-ink"
              >
                {s.title || "source"}
              </a>
            ))}
          </div>
        )}
      </div>

      <form onSubmit={onSend} className="flex gap-2 border-t border-line p-3">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about a company…"
          className="flex-1 rounded border border-line bg-paper px-3 py-2 text-sm text-ink placeholder:text-inksoft/70 focus:border-ink focus:outline-none"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="rounded bg-ink px-3 py-2 text-sm text-paper disabled:opacity-40"
        >
          Send
        </button>
      </form>
    </div>
  );
}
