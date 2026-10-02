"use client";

import { useEffect, useState } from "react";
import { getDecision, type DecisionResponse } from "@/lib/api";

type Props = {
  productId: number | null;
  userId?: number;
};

const DECISION_LABELS: Record<string, string> = {
  BUY: "BUY",
  WAIT: "WAIT",
  SUBSTITUTE: "SUBSTITUTE",
  NO_ACTION: "NO ACTION",
};

export default function DecisionCard({
  productId,
  userId,
}: Props) {
  const [decision, setDecision] = useState<DecisionResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (productId === null) {
      setDecision(null);
      return;
    }

    const selectedProductId = productId;
    let cancelled = false;

    async function loadDecision() {
      setLoading(true);

      try {
        const result = await getDecision(
          selectedProductId,
          userId,
        );

        if (!cancelled) {
          setDecision(result);
        }
      } catch {
        if (!cancelled) {
          setDecision(null);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadDecision();

    return () => {
      cancelled = true;
    };
  }, [productId, userId]);

  if (productId === null) {
    return null;
  }

  return (
    <section className="rounded-sm border border-line bg-white">
      <div className="border-b border-line px-5 py-3">
        <p className="font-display text-xs italic text-ink/60">
          product decision
        </p>
      </div>

      <div className="px-5 py-5">
        {loading && (
          <div className="space-y-3">
            <div className="h-5 w-2/3 animate-pulse rounded bg-savings-dim" />
            <div className="h-4 w-1/3 animate-pulse rounded bg-savings-dim" />
            <div className="h-4 w-full animate-pulse rounded bg-savings-dim" />
          </div>
        )}

        {!loading && !decision && (
          <p className="text-sm text-ink/50">
            Decision unavailable.
          </p>
        )}

        {!loading && decision && (
          <>
            <div className="flex items-baseline justify-between gap-4">
              <h2 className="font-display text-xl text-ink">
                {decision.product_name}
              </h2>

              <span className="font-mono text-sm text-savings">
                {DECISION_LABELS[decision.decision] ?? decision.decision}
              </span>
            </div>

            {decision.confidence > 0 && (
              <p className="mt-2 font-mono text-xs text-ink/50">
                {(decision.confidence * 100).toFixed(0)}% confidence
              </p>
            )}

            <div className="mt-4 border-t border-dashed border-line pt-4">
              <p className="text-sm leading-6 text-ink/80">
                {decision.reason}
              </p>
            </div>

            {decision.price_probability && (
              <div className="mt-4 border-t border-line pt-4">
                <p className="font-display text-xs italic text-ink/50">
                  price signal
                </p>

                <div className="mt-2 grid grid-cols-3 gap-3 font-mono text-xs">
                  <div>
                    <p className="text-ink/40">Increase</p>
                    <p className="mt-1">
                      {(decision.price_probability.INCREASE * 100).toFixed(0)}%
                    </p>
                  </div>

                  <div>
                    <p className="text-ink/40">Stable</p>
                    <p className="mt-1">
                      {(decision.price_probability.STABLE * 100).toFixed(0)}%
                    </p>
                  </div>

                  <div>
                    <p className="text-ink/40">Decrease</p>
                    <p className="mt-1">
                      {(decision.price_probability.DECREASE * 100).toFixed(0)}%
                    </p>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </section>
  );
}
