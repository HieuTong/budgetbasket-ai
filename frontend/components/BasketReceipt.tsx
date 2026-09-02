import type { OptimizeResponse } from "@/lib/api";

type Props = {
  basket: OptimizeResponse | null;
  loading: boolean;
};

export default function BasketReceipt({ basket, loading }: Props) {
  return (
    <div className="torn-top bg-white shadow-sm ring-1 ring-line/60">
      <div className="px-6 pt-6 pb-5">
        <p className="font-display text-xs italic text-ink/50">your basket</p>

        {loading && (
          <div className="mt-4 space-y-3">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-4 w-full animate-pulse rounded bg-savings-dim" />
            ))}
          </div>
        )}

        {!loading && !basket && (
          <p className="mt-4 text-sm text-ink/50">
            Set a budget above and the optimizer will fill your basket.
          </p>
        )}

        {!loading && basket && (
          <>
            <ul className="mt-4 space-y-2.5">
              {basket.items.map((item) => (
                <li key={item.name} className="leader font-mono text-sm">
                  <span className="font-sans">
                    {item.qty}× {item.name}
                  </span>
                  <span className="fill" aria-hidden />
                  <span>${(item.qty * item.unit_price).toFixed(2)}</span>
                </li>
              ))}
            </ul>

            <div className="mt-5 border-t border-dashed border-line pt-3">
              <div className="leader font-mono text-base font-medium">
                <span className="font-sans">Total</span>
                <span className="fill" aria-hidden />
                <span className="text-savings">${basket.total_cost.toFixed(2)}</span>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
