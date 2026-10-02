"use client";

import { useEffect, useState } from "react";
import {
  getSubstitutes,
  type Substitute,
  type SubstitutesResponse,
} from "@/lib/api";

type Props = {
  productId: number | null;
  userId?: number;
};

export default function SubstituteCard({
  productId,
  userId,
}: Props) {
  const [data, setData] = useState<SubstitutesResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (productId === null) {
      setData(null);
      return;
    }

    const selectedProductId = productId;
    let cancelled = false;

    async function loadSubstitutes() {
      setLoading(true);

      try {
        const result = await getSubstitutes(
          selectedProductId,
          userId,
          3,
        );

        if (!cancelled) {
          setData(result);
        }
      } catch {
        if (!cancelled) {
          setData(null);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadSubstitutes();

    return () => {
      cancelled = true;
    };
  }, [productId, userId]);

  if (productId === null) {
    return null;
  }

  return (
    <section className="rounded-sm bg-savings-dim">
      <div className="border-b border-line px-5 py-3">
        <p className="font-display text-xs italic text-ink/60">
          cheaper alternatives
        </p>
      </div>

      <div className="px-5 py-4">
        {loading && (
          <div className="space-y-3">
            {[0, 1, 2].map((item) => (
              <div
                key={item}
                className="h-12 animate-pulse rounded bg-white/60"
              />
            ))}
          </div>
        )}

        {!loading && !data && (
          <p className="text-sm text-ink/50">
            Alternatives unavailable.
          </p>
        )}

        {!loading && data && data.results.length === 0 && (
          <p className="text-sm text-ink/50">
            No cheaper alternatives found.
          </p>
        )}

        {!loading && data && data.results.length > 0 && (
          <ul className="divide-y divide-line">
            {data.results.map((item: Substitute) => (
              <li
                key={item.product_id}
                className="py-3 first:pt-0 last:pb-0"
              >
                <div className="flex items-baseline justify-between gap-4">
                  <div>
                    <p className="text-sm text-ink">
                      {item.product_name}
                    </p>

                    <p className="mt-0.5 text-xs text-ink/40">
                      {item.brand}
                    </p>
                  </div>

                  <p className="shrink-0 font-mono text-sm">
                    ${item.unit_price.toFixed(2)}
                  </p>
                </div>

                <div className="mt-1 flex gap-3 font-mono text-xs text-savings">
                  <span>
                    save ${item.savings.toFixed(2)}
                  </span>

                  <span>
                    {item.savings_percent.toFixed(0)}% less
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
