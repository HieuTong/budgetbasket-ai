"use client";

import { useEffect, useId, useRef, useState } from "react";

// Shown in turn while the assistant works, so a long wait doesn't look frozen.
const PROGRESS_MESSAGES = [
  "Reading your question…",
  "Checking products and prices…",
  "Writing the answer…",
];
import {
  askAgent,
  TimeoutError,
  type ChatStep,
  type ChatTurn,
} from "@/lib/api";

// How many earlier messages to send, so follow-ups like "what about bread?" make sense.
const HISTORY_TURNS = 8;

type Message = {
  id: number;
  role: "user" | "agent";
  text: string;
  error?: boolean;
  steps?: ChatStep[];
  // For failed replies: the question to ask again, and which message it was.
  retry?: { questionId: number; question: string };
};

// Each suggestion maps to something the assistant can actually do with its tools.
const SUGGESTIONS = [
  "build me a $60 basket",
  "should I buy milk now or wait?",
  "how has bread's price changed lately?",
  "find a cheaper swap for cheese",
];

export default function AgentChat({ userId }: { userId: number }) {
  const inputId = useId();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);

  const conversationRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const pending = useRef(false);
  const messageId = useRef(0);
  const generation = useRef(0);

  useEffect(() => {
    generation.current += 1;
    pending.current = false;
    setMessages([]);
    setInput("");
    setSending(false);

    return () => {
      generation.current += 1;
    };
  }, [userId]);

  useEffect(() => {
    const element = conversationRef.current;
    if (element) {
      element.scrollTop = element.scrollHeight;
    }
  }, [messages, sending]);

  async function handleSend(text?: string, earlier: Message[] = messages) {
    const question = (text ?? input).trim();
    if (!question || pending.current) return;

    pending.current = true;
    const requestGeneration = generation.current;

    // Earlier turns, oldest first. Failed replies are left out: they aren't real answers.
    const history: ChatTurn[] = earlier
      .filter((message) => !message.error)
      .slice(-HISTORY_TURNS)
      .map((message) => ({
        role: message.role === "user" ? "user" : "assistant",
        text: message.text,
      }));

    // Keep state updaters pure, including in React Strict Mode.
    const userMessage: Message = {
      id: ++messageId.current,
      role: "user",
      text: question,
    };

    setMessages((previous) => [...previous, userMessage]);
    setInput("");
    setSending(true);

    try {
      const { reply, steps } = await askAgent(userId, question, history);

      if (generation.current !== requestGeneration) return;

      const replyMessage: Message = {
        id: ++messageId.current,
        role: "agent",
        text: reply,
        steps,
      };

      setMessages((previous) => [...previous, replyMessage]);
    } catch (error) {
      if (generation.current !== requestGeneration) return;

      const errorMessage: Message = {
        id: ++messageId.current,
        role: "agent",
        error: true,
        retry: { questionId: userMessage.id, question },
        text:
          error instanceof TimeoutError
            ? "The assistant is taking longer than usual. Please try again in a moment."
            : "Couldn't reach the assistant. Please try again shortly.",
      };

      setMessages((previous) => [...previous, errorMessage]);
    } finally {
      if (generation.current === requestGeneration) {
        pending.current = false;
        setSending(false);
      }
    }
  }

  // One tap asks the question, instead of filling the box and waiting for "Send".
  function selectSuggestion(question: string) {
    void handleSend(question);
  }

  // Ask a failed question again, without leaving the failed attempt in the conversation.
  function retry(failed: Message) {
    if (!failed.retry || pending.current) return;
    const { questionId, question } = failed.retry;
    const earlier = messages.filter(
      (message) => message.id !== failed.id && message.id !== questionId,
    );
    setMessages(earlier);
    void handleSend(question, earlier);
  }

  function startOver() {
    generation.current += 1;
    pending.current = false;
    setMessages([]);
    setInput("");
    setSending(false);
    inputRef.current?.focus();
  }

  return (
    <section className="bb-card bb-chat" aria-label="Ask the assistant">
      <div className="bb-section-heading">
        <h2 className="bb-section-title">ask the assistant</h2>
        {messages.length > 0 && (
          <button
            type="button"
            className="bb-text-button"
            onClick={startOver}
            disabled={sending}
          >
            Start over
          </button>
        )}
      </div>

      <p className="bb-chat-description">
        A second opinion for your weekly shop.
      </p>

      <div
        ref={conversationRef}
        className="bb-conversation"
        role="log"
        aria-label="Assistant conversation"
        aria-live="polite"
        aria-relevant="additions text"
      >
        {messages.length === 0 && (
          <p className="bb-empty">
            Try: “build me a $60 basket” or “should I buy milk now or
            wait?”
          </p>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            className={`bb-message bb-message-${message.role}`}
          >
            <p className="bb-message-label">
              {message.role === "user" ? "You" : "Assistant"}
            </p>
            <div
              className={`bb-message-bubble${message.error ? " bb-message-error" : ""}`}
            >
              {message.text}
            </div>
            {message.error && message.retry && (
              <button
                type="button"
                className="bb-text-button bb-retry"
                onClick={() => retry(message)}
                disabled={sending}
              >
                Ask again
              </button>
            )}
            {message.steps && message.steps.length > 0 && (
              <ul className="bb-steps" aria-label="What the assistant did">
                {message.steps.map((step, index) => (
                  <li
                    key={`${step.tool}-${index}`}
                    className={step.ok ? undefined : "bb-step-failed"}
                  >
                    <span aria-hidden="true">{step.ok ? "✓" : "!"}</span>{" "}
                    {step.label}
                    {!step.ok && <span className="bb-sr-only"> (failed)</span>}
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}

        {sending && (
          <p className="bb-thinking" role="status">
            <ProgressText />
          </p>
        )}
      </div>

      <div className="bb-suggestions">
        <p className="bb-micro">Try asking</p>
        {SUGGESTIONS.map((question) => (
          <button
            key={question}
            type="button"
            disabled={sending}
            onClick={() => selectSuggestion(question)}
          >
            <span>{question}</span>
            <span aria-hidden="true">↗</span>
          </button>
        ))}
      </div>

      <form
        className="bb-chat-form"
        onSubmit={(event) => {
          event.preventDefault();
          void handleSend();
        }}
      >
        <label className="bb-sr-only" htmlFor={inputId}>
          Ask about your basket
        </label>
        <input
          ref={inputRef}
          id={inputId}
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={(event) => {
            if (
              event.key === "Enter" &&
              event.nativeEvent.isComposing
            ) {
              event.preventDefault();
            }
          }}
          placeholder="Ask about your basket…"
          autoComplete="off"
        />
        <button
          className="bb-button"
          type="submit"
          disabled={sending || !input.trim()}
        >
          Send
        </button>
      </form>

      <p className="bb-card-footnote">
        Suggestions only—your basket isn’t changed automatically.
      </p>
    </section>
  );
}

function ProgressText() {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(
      () => setIndex((value) => Math.min(value + 1, PROGRESS_MESSAGES.length - 1)),
      2500,
    );
    return () => window.clearInterval(timer);
  }, []);

  return <>{PROGRESS_MESSAGES[index]}</>;
}
