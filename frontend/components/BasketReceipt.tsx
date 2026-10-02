import type { OptimizeResponse } from "@/lib/api";

type Props = {
  basket: OptimizeResponse | null;
  loading: boolean;
  budget: number;
};

export default function BasketReceipt({
  basket,
  loading,
  budget,
}: Props) {
  const remaining = basket
    ? Math.max(0, budget - basket.total_cost)
    : 0;

  return (
    <div className="torn-top bg-white shadow-sm ring-1 ring-line/60">
      <div className="px-6 pt-6 pb-5">
        <div className="flex items-baseline justify-between">
          <p className="font-display text-xs italic text-ink/50">
            your basket
          </p>

          {basket && (
            <p className="font-mono text-xs text-ink/40">
              {basket.items.length} products
            </p>
          )}
        </div>

        {loading && (
          <div className="mt-4 space-y-3">
            {[0, 1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-4 w-full animate-pulse rounded bg-savings-dim"
              />
            ))}
          </div>
        )}

        {!loading && !basket && (
          <p className="mt-4 text-sm text-ink/50">
            Set a budget and optimize your basket.
          </p>
        )}

        {!loading && basket && (
          <>
            <ul className="mt-4 space-y-2.5">
              {basket.items.map((item) => (
                <li
                  key={item.name}
                  className="leader font-mono text-sm"
                >
                  <span className="font-sans">
                    {item.qty}× {item.name}
                  </span>

                  <span
                    className="fill"
                    aria-hidden
                  />

                  <span>
                    ${(item.qty * item.unit_price).toFixed(2)}
                  </span>
                </li>
              ))}
            </ul>

            <div className="mt-5 border-t border-dashed border-line pt-3">
              <div className="leader font-mono text-base font-medium">
                <span className="font-sans">
                  Total
                </span>

                <span
                  className="fill"
                  aria-hidden
                />

                <span className="text-savings">
                  ${basket.total_cost.toFixed(2)}
                </span>
              </div>

              <div className="leader mt-2 font-mono text-xs text-ink/50">
                <span className="font-sans">
                  Budget
                </span>

                <span
                  className="fill"
                  aria-hidden
                />

                <span>
                  ${budget.toFixed(2)}
                </span>
              </div>

              <div className="leader mt-1 font-mono text-xs text-ink/50">
                <span className="font-sans">
                  Remaining
                </span>

                <span
                  className="fill"
                  aria-hidden
                />

                <span>
                  ${remaining.toFixed(2)}
                </span>
              </div>
            </div>

            <div className="mt-4 border-t border-line pt-3">
              <div className="leader font-mono text-xs">
                <span className="font-sans text-ink/60">
                  Basket utility
                </span>

                <span
                  className="fill"
                  aria-hidden
                />

                <span className="text-ink">
                  {basket.total_utility.toFixed(2)}
                </span>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
