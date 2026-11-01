import { MAX_QTY, type BasketLine } from "@/lib/basket";

type Props = {
  lines: BasketLine[] | null;
  total: number | null;
  loading: boolean;
  budget: number;
  // A short description of the last change, announced to screen readers.
  lastChange: string;
  onSelectLine: (line: BasketLine) => void;
  onChangeQty: (productId: number, delta: number) => void;
  onRemove: (productId: number) => void;
  onClear: () => void;
  selectedProductId?: number | null;
};

export default function BasketReceipt({
  lines,
  total,
  loading,
  budget,
  lastChange,
  onSelectLine,
  onChangeQty,
  onRemove,
  onClear,
  selectedProductId = null,
}: Props) {
  const spent = total ?? 0;
  const remaining = budget - spent;
  const itemCount = lines?.reduce((sum, line) => sum + line.qty, 0) ?? 0;
  const usedPercent = budget > 0 ? Math.round((spent / budget) * 100) : 0;

  return (
    <section className="bb-receipt-shell" aria-label="Your basket">
      <div className="bb-receipt" aria-busy={loading}>
        <div className="bb-section-heading">
          <h2 className="bb-section-title">your basket</h2>
          {lines && lines.length > 0 && (
            <button type="button" className="bb-text-button" onClick={onClear}>
              Clear
            </button>
          )}
        </div>

        <div className="bb-receipt-meta">
          <span>Weekly shop</span>
          <span>
            {itemCount} {itemCount === 1 ? "item" : "items"}
          </span>
        </div>

        {/* Announces "Added milk." and similar changes without moving focus. */}
        <p className="bb-sr-only" role="status" aria-live="polite">
          {lastChange}
        </p>

        {loading ? (
          <div className="bb-skeleton-group" role="status">
            <span className="bb-sr-only">Building your basket</span>
            {[0, 1, 2, 3, 4, 5].map((item) => (
              <div className="bb-skeleton" key={item} />
            ))}
          </div>
        ) : lines ? (
          <>
            {lines.length > 0 ? (
              <ul className="bb-receipt-items">
                {lines.map((line) => (
                  <li className="bb-receipt-line" key={line.productId}>
                    <div className="bb-leader">
                      <button
                        type="button"
                        className="bb-item-name bb-item-button"
                        aria-pressed={selectedProductId === line.productId}
                        aria-label={`${line.name}: see buy-or-wait advice and cheaper swaps`}
                        onClick={() => onSelectLine(line)}
                      >
                        {line.name}
                      </button>
                      <span className="bb-leader-fill" aria-hidden="true" />
                      <span className="bb-price">
                        ${((Math.round(line.unitPrice * 100) * line.qty) / 100).toFixed(2)}
                      </span>
                    </div>

                    <div className="bb-line-controls">
                      <div className="bb-stepper" role="group" aria-label={`Quantity of ${line.name}`}>
                        <button
                          type="button"
                          aria-label={line.qty === 1 ? `Remove ${line.name}` : `One less ${line.name}`}
                          onClick={() => onChangeQty(line.productId, -1)}
                        >
                          −
                        </button>
                        <span aria-live="polite">{line.qty}</span>
                        <button
                          type="button"
                          aria-label={`One more ${line.name}`}
                          disabled={line.qty >= MAX_QTY}
                          onClick={() => onChangeQty(line.productId, 1)}
                        >
                          +
                        </button>
                      </div>

                      <span className="bb-line-note">
                        {line.origin === "swapped" && line.swappedFrom
                          ? `Swapped from ${line.swappedFrom}`
                          : line.origin === "added"
                            ? "Added by you"
                            : `$${line.unitPrice.toFixed(2)} each`}
                      </span>

                      <button
                        type="button"
                        className="bb-text-button bb-line-remove"
                        aria-label={`Remove ${line.name} from basket`}
                        onClick={() => onRemove(line.productId)}
                      >
                        Remove
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="bb-empty">
                Your basket is empty. Build it again, or add products from the
                search.
              </p>
            )}

            <dl className="bb-receipt-totals">
              <div className="bb-total-row">
                <dt>Total</dt>
                <dd>${spent.toFixed(2)}</dd>
              </div>
              <div>
                <dt>Budget</dt>
                <dd>${budget.toFixed(2)}</dd>
              </div>
              <div className={remaining < 0 ? "bb-negative" : "bb-green"}>
                <dt>{remaining < 0 ? "Over budget" : "Remaining"}</dt>
                <dd>${Math.abs(remaining).toFixed(2)}</dd>
              </div>
            </dl>

            <div className="bb-budget-meter">
              <progress
                max={budget}
                value={Math.min(spent, budget)}
                aria-label={`${usedPercent}% of your budget used`}
                className={remaining < 0 ? "bb-meter-over" : undefined}
              />
              <p className="bb-micro">
                {remaining < 0
                  ? `$${Math.abs(remaining).toFixed(2)} over your budget`
                  : `${usedPercent}% of your budget used`}
              </p>
            </div>

            {lines.length > 0 && (
              <p className="bb-card-footnote">
                Select an item for buy-or-wait advice and cheaper swaps.
              </p>
            )}
          </>
        ) : (
          <p className="bb-empty">
            Pick a weekly budget, then build your basket. It's filled with the
            products you usually buy. You can also add products yourself from
            the search.
          </p>
        )}
      </div>
    </section>
  );
}
