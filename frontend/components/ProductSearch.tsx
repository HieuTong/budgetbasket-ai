"use client";

import { useEffect, useState } from "react";
import { getProducts, type Product } from "@/lib/api";

type Props = {
  selectedProductId: number | null;
  onSelect: (product: Product) => void;
};

export default function ProductSearch({
  selectedProductId,
  onSelect,
}: Props) {
  const [query, setQuery] = useState("");
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const trimmedQuery = query.trim();

    if (!trimmedQuery) {
      setProducts([]);
      setLoading(false);
      return;
    }

    let cancelled = false;

    const timer = window.setTimeout(async () => {
      setLoading(true);

      try {
        const result = await getProducts(
          undefined,
          trimmedQuery,
          8,
        );

        if (!cancelled) {
          setProducts(result.items);
        }
      } catch {
        if (!cancelled) {
          setProducts([]);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }, 300);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [query]);

  const hasQuery = query.trim().length > 0;

  return (
    <section className="rounded-sm border border-line bg-white">
      <div className="border-b border-line px-5 py-3">
        <p className="font-display text-xs italic text-ink/60">
          choose a product
        </p>
      </div>

      <div className="px-5 py-4">
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search your grocery catalog…"
          className="w-full border-b border-line bg-transparent py-2 text-sm outline-none placeholder:text-ink/30 focus:border-savings"
        />

        {loading && (
          <p className="mt-4 text-sm text-ink/40">
            searching…
          </p>
        )}

        {!loading && hasQuery && products.length === 0 && (
          <p className="mt-4 text-sm text-ink/40">
            No matching products.
          </p>
        )}

        {!loading && products.length > 0 && (
          <ul className="mt-3 divide-y divide-line">
            {products.map((product) => (
              <li key={product.id}>
                <button
                  type="button"
                  onClick={() => onSelect(product)}
                  className={`w-full py-3 text-left transition ${
                    selectedProductId === product.id
                      ? "text-savings"
                      : "text-ink"
                  }`}
                >
                  <div className="flex items-baseline justify-between gap-4">
                    <span className="text-sm">
                      {product.name}
                    </span>

                    <span className="shrink-0 font-mono text-sm">
                      ${product.unit_price.toFixed(2)}
                    </span>
                  </div>

                  <p className="mt-0.5 text-xs text-ink/40">
                    {product.brand}
                    {product.sub_category
                      ? ` · ${product.sub_category}`
                      : ""}
                  </p>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
