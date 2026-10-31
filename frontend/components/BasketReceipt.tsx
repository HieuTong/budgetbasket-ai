import type { BasketItem, OptimizeResponse } from "@/lib/api";

type Props = {
  basket: OptimizeResponse | null;
  loading: boolean;
  budget: number;
  // Lets each basket item open its buy-or-wait advice and cheaper swaps.
  onSelectItem?: (item: BasketItem) => void;
  selectedProductId?: number | null;
};

export default function BasketReceipt({
  basket,
  loading,
  budget,
  onSelectItem,
  selectedProductId = null,
}: Props) {
  const remaining = basket ? budget - basket.total_cost : 0;
  const itemCount =
    basket?.items.reduce((sum, item) => sum + item.qty, 0) ?? 0;

  return (
    <section className="bb-receipt-shell" aria-label="Your basket">
      <div className="bb-receipt" aria-busy={loading}>
        <div className="bb-section-heading">
          <h2 className="bb-section-title">your basket</h2>
          {basket && (
            <span className="bb-micro">
              {basket.items.length} products
            </span>
          )}
        </div>

        <div className="bb-receipt-meta">
          <span>Weekly shop</span>
          <span>{itemCount} items</span>
        </div>

        {loading ? (
          <div className="bb-skeleton-group" role="status">
            <span className="bb-sr-only">Optimizing your basket</span>
            {[0, 1, 2, 3, 4, 5].map((item) => (
              <div className="bb-skeleton" key={item} />
            ))}
          </div>
        ) : basket ? (
          <>
            {basket.items.length > 0 ? (
              <ul className="bb-receipt-items">
                {basket.items.map((item, index) => (
                  <li
                    className="bb-leader"
                    key={`${item.product_id ?? item.name}-${index}`}
                  >
                    {onSelectItem ? (
                      <button
                        type="button"
                        className="bb-item-name bb-item-button"
                        aria-pressed={selectedProductId === item.product_id}
                        aria-label={`${item.qty} × ${item.name}: see buy-or-wait advice and cheaper swaps`}
                        onClick={() => onSelectItem(item)}
                      >
                        <span className="bb-quantity">{item.qty} × </span>
                        {item.name}
                      </button>
                    ) : (
                      <span className="bb-item-name">
                        <span className="bb-quantity">{item.qty} × </span>
                        {item.name}
                      </span>
                    )}
                    <span
                      className="bb-leader-fill"
                      aria-hidden="true"
                    />
                    <span className="bb-price">
                      ${(item.qty * item.unit_price).toFixed(2)}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="bb-empty">
                No products were returned for this budget.
              </p>
            )}

            {onSelectItem && basket.items.length > 0 && (
              <p className="bb-card-footnote">
                Select an item to see whether to buy now or wait, and cheaper swaps.
              </p>
            )}

            <dl className="bb-receipt-totals">
              <div className="bb-total-row">
                <dt>Total</dt>
                <dd>${basket.total_cost.toFixed(2)}</dd>
              </div>
              <div>
                <dt>Budget</dt>
                <dd>${budget.toFixed(2)}</dd>
              </div>
              <div
                className={remaining < 0 ? "bb-negative" : "bb-green"}
              >
                <dt>{remaining < 0 ? "Over budget" : "Remaining"}</dt>
                <dd>${Math.abs(remaining).toFixed(2)}</dd>
              </div>
            </dl>

            <div className="bb-budget-meter">
              <progress
                max={budget}
                value={Math.min(basket.total_cost, budget)}
                aria-label={`${Math.round((basket.total_cost / budget) * 100)}% of your budget used`}
                className={remaining < 0 ? "bb-meter-over" : undefined}
              />
              <p className="bb-micro">
                {remaining < 0
                  ? `$${Math.abs(remaining).toFixed(2)} over your budget`
                  : `${Math.round((basket.total_cost / budget) * 100)}% of your budget used`}
              </p>
            </div>
          </>
        ) : (
          <p className="bb-empty">
            Pick a weekly budget, then build your basket. It's filled with the
            products you usually buy.
          </p>
        )}
      </div>
    </section>
  );
}
