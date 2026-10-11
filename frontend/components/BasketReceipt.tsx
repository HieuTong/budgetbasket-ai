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
          <span>WEEKLY SHOP</span>
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
                    key={`${item.name}-${index}`}
                  >
                    <span className="bb-item-name">
                      <span className="bb-quantity">{item.qty} × </span>
                      {item.name}
                    </span>
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

            <div className="bb-utility">
              <span>Basket utility</span>
              <span className="bb-mono">
                {basket.total_utility.toFixed(2)}
              </span>
            </div>
          </>
        ) : (
          <p className="bb-empty">
            Set a budget and optimize your basket.
          </p>
        )}
      </div>
    </section>
  );
}
