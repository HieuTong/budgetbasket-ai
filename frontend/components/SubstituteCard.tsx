"use client";

import { useEffect, useState } from "react";
import {
  getSubstitutes,
  type SubstitutesResponse,
} from "@/lib/api";

type Props = {
  productId: number | null;
  userId?: number;
};

type RequestState = {
  productId: number;
  userId: number | undefined;
  status: "loading" | "success" | "error";
  data: SubstitutesResponse | null;
};

export default function SubstituteCard({
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

    getSubstitutes(id, userId, 3)
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
  const data = current?.data;

  return (
    <section
      className="bb-card bb-alternatives"
      aria-label="Cheaper alternatives"
      aria-busy={loading}
    >
      <div className="bb-section-heading">
        <h2 className="bb-section-title">cheaper alternatives</h2>
        {data && (
          <span className="bb-micro bb-green">
            vs. ${data.base_price.toFixed(2)}
          </span>
        )}
      </div>

      {loading ? (
        <div className="bb-skeleton-group" role="status">
          <span className="bb-sr-only">Loading alternatives</span>
          {[0, 1, 2].map((item) => (
            <div key={item} className="bb-skeleton" />
          ))}
        </div>
      ) : current?.status === "error" || !data ? (
        <div className="bb-empty">
          <p role="alert">Alternatives unavailable.</p>
          <button
            className="bb-text-button"
            type="button"
            onClick={() => setRetry((value) => value + 1)}
          >
            Try again
          </button>
        </div>
      ) : data.results.length === 0 ? (
        <p className="bb-empty">No cheaper alternatives found.</p>
      ) : (
        <>
          <ul className="bb-substitute-list">
            {data.results.map((item, index) => (
              <li key={item.product_id}>
                <div className="bb-substitute-row">
                  <div className="bb-substitute-copy">
                    <h3>
                      {item.product_name}
                      {index === 0 && (
                        <span className="bb-best-value">
                          TOP MATCH
                        </span>
                      )}
                    </h3>
                    <p className="bb-product-detail">{item.brand}</p>
                  </div>

                  <div className="bb-substitute-pricing">
                    <p className="bb-price">
                      ${item.unit_price.toFixed(2)}
                    </p>
                    <p className="bb-savings">
                      save ${item.savings.toFixed(2)} ·{" "}
                      {item.savings_percent.toFixed(0)}% less
                    </p>
                  </div>
                </div>

                {item.reason && (
                  <p className="bb-substitute-reason">
                    {item.reason}
                  </p>
                )}
              </li>
            ))}
          </ul>

          <p className="bb-card-footnote">
            Savings shown per unit. Your basket is unchanged.
          </p>
        </>
      )}
    </section>
  );
}
