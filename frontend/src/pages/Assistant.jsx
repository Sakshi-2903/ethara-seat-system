import { useState, useRef, useEffect } from "react";
import { api } from "../api.js";

const SUGGESTIONS = [
  "Where is employee Amit seated?",
  "Show all available seats on Floor 3.",
  "How many seats are occupied for Project Indigo?",
  "Who is sitting near Amit?",
];

export default function Assistant() {
  const [email, setEmail] = useState("");
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      text:
        "Hi, I'm the Ethara seating assistant. Ask me where someone sits, which project they're on, or which seats are free on a floor.",
    },
  ]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send(text) {
    const query = (text ?? input).trim();
    if (!query || sending) return;
    setMessages((m) => [...m, { role: "user", text: query }]);
    setInput("");
    setSending(true);
    try {
      const payload = { query };
      if (email) payload.email = email;
      const res = await api.aiQuery(payload);
      setMessages((m) => [...m, { role: "assistant", text: res.answer, intent: res.intent }]);
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", text: `Sorry, something went wrong: ${e.message}` }]);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="max-w-3xl mx-auto px-4 md:px-8 py-8 flex flex-col h-[calc(100vh-3.5rem)] md:h-screen">
      <header className="mb-4 shrink-0">
        <p className="text-[11px] font-semibold tracking-wider uppercase text-signal-dark mb-1">
          Ask Ethara
        </p>
        <h1 className="font-display text-2xl md:text-3xl font-semibold text-ink">
          Seat &amp; project assistant
        </h1>
        <p className="text-sm text-slate mt-1">
          Rule-based natural language assistant — answers are grounded directly in the seat
          allocation database (no hallucinated seat numbers).
        </p>
      </header>

      <div className="mb-4 shrink-0">
        <label className="block text-xs font-medium text-slate mb-1">
          Your email (optional — lets you ask "Where is my seat?")
        </label>
        <input
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@ethara.ai"
          className="w-full sm:w-80 px-3 py-2 rounded-lg border border-border bg-white text-sm"
        />
      </div>

      <div className="flex-1 card overflow-y-auto scrollbar-thin p-4 space-y-3 mb-4">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[85%] px-4 py-2.5 rounded-2xl text-sm ${
                m.role === "user"
                  ? "bg-ink text-white rounded-br-sm"
                  : "bg-paper-dim text-ink rounded-bl-sm"
              }`}
            >
              {m.text}
            </div>
          </div>
        ))}
        {sending && (
          <div className="flex justify-start">
            <div className="px-4 py-2.5 rounded-2xl rounded-bl-sm bg-paper-dim text-slate-light text-sm">
              Thinking…
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="flex flex-wrap gap-2 mb-3 shrink-0">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => send(s)}
            className="text-xs px-3 py-1.5 rounded-full border border-border bg-white text-slate hover:bg-paper-dim transition-colors"
          >
            {s}
          </button>
        ))}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
        className="flex gap-2 shrink-0"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about a seat, project, or floor…"
          className="flex-1 px-4 py-2.5 rounded-lg border border-border bg-white text-sm focus:outline-none focus:ring-2 focus:ring-signal/40"
        />
        <button
          type="submit"
          disabled={sending}
          className="px-5 py-2.5 rounded-lg bg-signal text-ink text-sm font-semibold hover:bg-signal-dark hover:text-white transition-colors disabled:opacity-50"
        >
          Ask
        </button>
      </form>
    </div>
  );
}
