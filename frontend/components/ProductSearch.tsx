"use client";

import { useEffect, useId, useState } from "react";
import { getProducts, type Product } from "@/lib/api";

type Props = {
  selectedProductId: number | null;
  onSelect: (product: Product) => void;
};

type SearchState = {
  query: string;
  items: Product[];
  status: "loading" | "success" | "error";
};

export default function ProductSearch({
  selectedProductId,
  onSelect,
}: Props) {
  const inputId = useId();
  const [query, setQuery] = useState("");
  const [state, setState] = useState<SearchState | null>(null);
  const [retry, setRetry] = useState(0);

  const trimmedQuery = query.trim();
  const current = state?.query === trimmedQuery ? state : null;
  const loading =
    trimmedQuery.length > 0 &&
    (!current || current.status === "loading");

  useEffect(() => {
    if (!trimmedQuery) {
      setState(null);
      return;
    }

    let cancelled = false;

    setState({
      query: trimmedQuery,
      items: [],
      status: "loading",
    });

    const timer = window.setTimeout(async () => {
      try {
        const result = await getProducts(undefined, trimmedQuery, 8);

        if (!cancelled) {
          setState({
            query: trimmedQuery,
            items: result.items,
            status: "success",
          });
        }
      } catch {
        if (!cancelled) {
          setState({
            query: trimmedQuery,
            items: [],
            status: "error",
          });
        }
      }
    }, 300);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [trimmedQuery, retry]);

  return (
    <section
      className="bb-card"
      aria-labelledby={`${inputId}-heading`}
    >
      <div className="bb-section-heading">
        <h2
          id={`${inputId}-heading`}
          className="bb-section-title"
        >
          choose a product
        </h2>
        <span className="bb-micro">Your catalog</span>
      </div>

      <div className="bb-search-field">
        <span aria-hidden="true">⌕</span>
        <label className="bb-sr-only" htmlFor={inputId}>
          Search your grocery catalog
        </label>
        <input
          id={inputId}
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search your grocery catalog…"
          autoComplete="off"
        />
      </div>

      <div aria-live="polite" aria-busy={loading}>
        {!trimmedQuery && (
          <p className="bb-empty">
            Search by product name to compare your options.
          </p>
        )}

        {loading && <p className="bb-empty">Searching…</p>}

        {current?.status === "error" && (
          <div className="bb-empty">
            <p role="alert">Couldn't load products.</p>
            <button
              className="bb-text-button"
              type="button"
              onClick={() => setRetry((value) => value + 1)}
            >
              Try again
            </button>
          </div>
        )}

        {current?.status === "success" &&
          current.items.length === 0 && (
            <p className="bb-empty">No matching products.</p>
          )}
      </div>

      {current?.status === "success" &&
        current.items.length > 0 && (
          <ul className="bb-product-list">
            {current.items.map((product) => {
              const selected = selectedProductId === product.id;

              return (
                <li key={product.id}>
                  <button
                    className={`bb-product-option${selected ? " is-selected" : ""}`}
                    type="button"
                    aria-pressed={selected}
                    onClick={() => onSelect(product)}
                  >
                    <span
                      className="bb-selection-dot"
                      aria-hidden="true"
                    >
                      {selected ? "✓" : ""}
                    </span>

                    <span className="bb-product-copy">
                      <span className="bb-product-name">
                        {product.name}
                      </span>
                      <span className="bb-product-detail">
                        {[
                          product.brand,
                          product.sub_category,
                          product.package_size,
                        ]
                          .filter(Boolean)
                          .join(" · ")}
                      </span>
                    </span>

                    <span className="bb-price bb-green">
                      ${product.unit_price.toFixed(2)}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
    </section>
  );
}
