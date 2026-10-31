"use client";

import { useEffect, useState } from "react";
import { getDecision, type DecisionResponse } from "@/lib/api";

type Props = {
  productId: number | null;
  userId?: number;
};

type RequestState = {
  productId: number;
  userId: number | undefined;
  status: "loading" | "success" | "error";
  data: DecisionResponse | null;
};

// Plain-language verdicts instead of internal codes like NO_ACTION.
const VERDICTS: Record<string, { title: string; hint: string }> = {
  BUY: { title: "Buy now", hint: "The price isn't expected to drop soon." },
  WAIT: { title: "Wait if you can", hint: "The price is likely to drop soon." },
  SUBSTITUTE: { title: "Consider a swap", hint: "A cheaper similar product is available." },
  NO_ACTION: {
    title: "No clear signal",
    hint: "There isn't enough price history to call it. Buy as you normally would.",
  },
};

function confidenceLabel(confidence: number): string {
  if (confidence >= 0.75) return "High confidence";
  if (confidence >= 0.5) return "Medium confidence";
  return "Low confidence";
}

export default function DecisionCard({
  productId,
  userId,
}: Props) {
  const [state, setState] = useState<RequestState | null>(null);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    if (productId === null) {
      setState(null);
      return;
    }

    let cancelled = false;
    const id = productId;

    setState({
      productId: id,
      userId,
      status: "loading",
      data: null,
    });

    getDecision(id, userId)
      .then((data) => {
        if (!cancelled) {
          setState({
            productId: id,
            userId,
            status: "success",
            data,
          });
        }
      })
      .catch(() => {
        if (!cancelled) {
          setState({
            productId: id,
            userId,
            status: "error",
            data: null,
          });
        }
      });

    return () => {
      cancelled = true;
    };
  }, [productId, userId, retry]);

  if (productId === null) return null;

  const current =
    state?.productId === productId && state.userId === userId
      ? state
      : null;

  const loading = !current || current.status === "loading";
  const decision = current?.data;
  const probabilities = decision?.price_probability;

  return (
    <section
      className="bb-card"
      aria-label="Product decision"
      aria-busy={loading}
    >
      <div className="bb-section-heading">
        <h2 className="bb-section-title">product decision</h2>
        <span className="bb-green" aria-hidden="true">✧</span>
      </div>

      {loading ? (
        <div className="bb-skeleton-group" role="status">
          <span className="bb-sr-only">Loading recommendation</span>
          <div className="bb-skeleton bb-skeleton-short" />
          <div className="bb-skeleton" />
          <div className="bb-skeleton" />
        </div>
      ) : current?.status === "error" || !decision ? (
        <div className="bb-empty">
          <p role="alert">Couldn't load advice for this product.</p>
          <button
            type="button"
            className="bb-text-button"
            onClick={() => setRetry((value) => value + 1)}
          >
            Try again
          </button>
        </div>
      ) : (
        <>
          <div className="bb-decision-head">
            <h3 className="bb-product-title">
              {decision.product_name}
            </h3>

            <div className="bb-decision-status">
              <span className="bb-badge">
                {VERDICTS[decision.decision]?.title ?? decision.decision}
              </span>

              {decision.confidence > 0 && (
                <span className="bb-micro">
                  {confidenceLabel(decision.confidence)} (
                  {(decision.confidence * 100).toFixed(0)}%)
                </span>
              )}
            </div>
          </div>

          {VERDICTS[decision.decision] && (
            <p className="bb-decision-hint">{VERDICTS[decision.decision].hint}</p>
          )}
          <p className="bb-decision-reason">{decision.reason}</p>

          {probabilities && (
            <div className="bb-price-signal">
              <div className="bb-section-heading">
                <h4 className="bb-section-title">price signal</h4>
              </div>

              <div className="bb-probability-grid">
                {(
                  [
                    ["Increase", probabilities.INCREASE],
                    ["Stable", probabilities.STABLE],
                    ["Decrease", probabilities.DECREASE],
                  ] as const
                ).map(([label, probability]) => (
                  <div key={label}>
                    <div className="bb-probability-label">
                      <span>{label}</span>
                      <span className="bb-mono">
                        {(probability * 100).toFixed(0)}%
                      </span>
                    </div>

                    <progress
                      max={1}
                      value={probability}
                      aria-label={`${label} probability`}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </section>
  );
}
