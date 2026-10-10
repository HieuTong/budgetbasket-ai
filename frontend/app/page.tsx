"use client";

import { useRef, useState } from "react";
import DashboardHeader from "@/components/DashboardHeader";
import BudgetSlider from "@/components/BudgetSlider";
import BasketReceipt from "@/components/BasketReceipt";
import ProductSearch from "@/components/ProductSearch";
import DecisionCard from "@/components/DecisionCard";
import SubstituteCard from "@/components/SubstituteCard";
import AgentChat from "@/components/AgentChat";
import SwapTips from "@/components/SwapTips";
import {
  optimizeBasket,
  type OptimizeResponse,
  type Product,
} from "@/lib/api";

// Retains your existing demo user.
// Replace with authenticated identity before a multi-user release.
const USER_ID = 1;

export default function Home() {
  const [budget, setBudget] = useState(85);
  const [basket, setBasket] = useState<OptimizeResponse | null>(null);
  const [basketBudget, setBasketBudget] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(
    null,
  );

  const optimizing = useRef(false);
  const basketIsStale = basket !== null && basketBudget !== budget;

  async function handleOptimize() {
    if (optimizing.current) return;

    optimizing.current = true;
    const requestedBudget = budget;

    setLoading(true);
    setError(null);

    try {
      const result = await optimizeBasket(USER_ID, requestedBudget);
      setBasket(result);
      setBasketBudget(requestedBudget);
    } catch {
      setError(
        "Couldn't optimize your basket. Check your connection and try again.",
      );
    } finally {
      optimizing.current = false;
      setLoading(false);
    }
  }

  return (
    <div className="bb-app">
      <DashboardHeader
        totalCost={basket?.total_cost ?? null}
        budget={budget}
        stale={basketIsStale}
      />

      <main id="main-content" className="bb-workspace" tabIndex={-1}>
        <section
          className="bb-column bb-basket-column"
          aria-label="Budget and basket"
        >
          <div className="bb-card bb-budget-card">
            <BudgetSlider
              budget={budget}
              onChange={setBudget}
              onOptimize={handleOptimize}
              loading={loading}
            />

            {error && (
              <p className="bb-error" role="alert">
                {error}
              </p>
            )}

            {basketIsStale && (
              <p className="bb-notice" role="status">
                This basket was optimized for ${basketBudget?.toFixed(0)}.
                Optimize again to use your new budget.
              </p>
            )}
          </div>

          <BasketReceipt
            basket={basket}
            loading={loading}
            budget={basketBudget ?? budget}
          />
        </section>

        <section
          className="bb-column bb-guidance-column"
          aria-label="Product guidance"
        >
          <ProductSearch
            selectedProductId={selectedProduct?.id ?? null}
            onSelect={setSelectedProduct}
          />

          {selectedProduct ? (
            <>
              <DecisionCard
                productId={selectedProduct.id}
                userId={USER_ID}
              />

              <SubstituteCard
                productId={selectedProduct.id}
                userId={USER_ID}
              />
            </>
          ) : (
            <section className="bb-card bb-guidance-empty">
              <p className="bb-section-title">
                a little guidance for your shop
              </p>
              <h2>Buy now, wait, or find a better swap.</h2>
              <p className="bb-muted">
                Search and choose a product to see its recommendation,
                price signal, and cheaper alternatives.
              </p>
            </section>
          )}
        </section>

        <aside
          className="bb-column bb-assistant-column"
          aria-label="Assistant and savings tips"
        >
          <AgentChat userId={USER_ID} />
          <SwapTips />
        </aside>
      </main>

      <footer className="bb-footer">
        <p>
          Prices reflect your connected catalog. AI guidance is an estimate.
        </p>
        <p className="bb-footer-signoff">
          A little planning. A fuller basket.
        </p>
      </footer>
    </div>
  );
}