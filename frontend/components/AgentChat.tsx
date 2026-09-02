"use client";

import { useState } from "react";
import { askAgent } from "@/lib/api";

type Message = { role: "user" | "agent"; text: string };

export default function AgentChat({ userId }: { userId: number }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);

  async function handleSend() {
    if (!input.trim() || sending) return;
    const question = input.trim();
    setMessages((m) => [...m, { role: "user", text: question }]);
    setInput("");
    setSending(true);
    try {
      const { reply } = await askAgent(userId, question);
      setMessages((m) => [...m, { role: "agent", text: reply }]);
    } catch {
      setMessages((m) => [
        ...m,
        { role: "agent", text: "Couldn't reach the assistant — check the backend is running." },
      ]);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="rounded-sm border border-line bg-white">
      <div className="border-b border-line px-5 py-3">
        <p className="font-display text-xs italic text-ink/60">ask the assistant</p>
      </div>

      <div className="max-h-64 space-y-3 overflow-y-auto px-5 py-4">
        {messages.length === 0 && (
          <p className="text-sm text-ink/40">
            Try: “swap something to save $5” or “why is bread more expensive this week?”
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "text-right" : "text-left"}>
            <span
              className={`inline-block max-w-[85%] rounded-sm px-3 py-2 text-sm ${
                m.role === "user" ? "bg-savings-dim text-ink" : "bg-paper text-ink/90"
              }`}
            >
              {m.text}
            </span>
          </div>
        ))}
        {sending && <p className="text-sm text-ink/40">thinking…</p>}
      </div>

      <div className="flex items-center gap-2 border-t border-line px-4 py-3">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Ask about your basket…"
          className="flex-1 bg-transparent text-sm outline-none placeholder:text-ink/30"
        />
        <button
          onClick={handleSend}
          disabled={sending}
          className="font-mono text-xs font-medium text-savings disabled:opacity-40"
        >
          Send
        </button>
      </div>
    </div>
  );
}
