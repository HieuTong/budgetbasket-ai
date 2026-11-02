"use client";

import { useEffect, useRef, useState } from "react";
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
  TimeoutError,
  type Product,
  type Substitute,
} from "@/lib/api";
import {
  addProduct,
  basketTotal,
  changeQty,
  fromOptimized,
  loadBasket,
  quantityOf,
  removeLine,
  saveBasket,
  swapLine,
  type BasketLine,
} from "@/lib/basket";

// Retains your existing demo user.
// Replace with authenticated identity before a multi-user release.
const USER_ID = 1;

export default function Home() {
  const [budget, setBudget] = useState(85);
  // null = no basket yet. The user can build one, or start by adding products.
  const [lines, setLines] = useState<BasketLine[] | null>(null);
  const [basketBudget, setBasketBudget] = useState<number | null>(null);
  // True once the user changes a built basket, so we can warn before rebuilding.
  const [edited, setEdited] = useState(false);
  const [lastChange, setLastChange] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(
    null,
  );
  const [restored, setRestored] = useState(false);

  const optimizing = useRef(false);
  const total = lines ? basketTotal(lines) : null;
  const basketIsStale =
    lines !== null && basketBudget !== null && basketBudget !== budget;

  // Restore the saved basket after the first render. Reading localStorage during render
  // would make the server-rendered HTML differ from the browser's, which React warns about.
  useEffect(() => {
    const saved = loadBasket(USER_ID);
    if (saved) {
      setLines(saved.lines);
      setBasketBudget(saved.builtFor);
      setEdited(saved.edited);
    }
    setRestored(true);
  }, []);

  useEffect(() => {
    if (!restored) return;
    saveBasket(
      USER_ID,
      lines === null ? null : { lines, builtFor: basketBudget, edited },
    );
  }, [lines, basketBudget, edited, restored]);

  async function handleOptimize() {
    if (optimizing.current) return;

    optimizing.current = true;
    const requestedBudget = budget;

    setLoading(true);
    setError(null);

    try {
      const result = await optimizeBasket(USER_ID, requestedBudget);
      setLines(fromOptimized(result));
      setBasketBudget(requestedBudget);
      setEdited(false);
      setLastChange(`Built a basket for $${requestedBudget}.`);
    } catch (failure) {
      setError(
        failure instanceof TimeoutError
          ? "Building your basket is taking longer than usual. Please try again in a moment."
          : "Couldn't build your basket. Check your connection and try again.",
      );
    } finally {
      optimizing.current = false;
      setLoading(false);
    }
  }

  function updateLines(next: BasketLine[], message: string) {
    setLines(next.length > 0 || basketBudget !== null ? next : null);
    setEdited(true);
    setLastChange(message);
  }

  function addSelectedProduct() {
    if (!selectedProduct) return;
    updateLines(
      addProduct(lines ?? [], {
        productId: selectedProduct.id,
        name: selectedProduct.name,
        unitPrice: selectedProduct.unit_price,
      }),
      `Added ${selectedProduct.name}.`,
    );
  }

  function applySubstitute(substitute: Substitute) {
    if (!selectedProduct) return;
    const replacement = {
      productId: substitute.product_id,
      name: substitute.product_name,
      unitPrice: substitute.unit_price,
    };
    const replacing = quantityOf(lines, selectedProduct.id) > 0;

    updateLines(
      replacing
        ? swapLine(lines ?? [], selectedProduct.id, replacement)
        : addProduct(lines ?? [], replacement),
      replacing
        ? `Swapped ${selectedProduct.name} for ${substitute.product_name}.`
        : `Added ${substitute.product_name}.`,
    );

    // Show advice for the product that's now in the basket.
    setSelectedProduct({
      id: substitute.product_id,
      name: substitute.product_name,
      brand: substitute.brand,
      category: substitute.category,
      unit_price: substitute.unit_price,
    });
  }

  function selectBasketLine(line: BasketLine) {
    setSelectedProduct({
      id: line.productId,
      name: line.name,
      brand: "",
      category: "",
      unit_price: line.unitPrice,
    });
    // On narrow screens the advice is further down the page, so bring it into view.
    document
      .getElementById("product-guidance")
      ?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function clearBasket() {
    setLines(null);
    setBasketBudget(null);
    setEdited(false);
    setLastChange("Cleared your basket.");
  }

  return (
    <div className="bb-app">
      <DashboardHeader
        totalCost={total}
        budget={basketBudget ?? budget}
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

            {edited && lines !== null && lines.length > 0 && (
              <p className="bb-notice">
                You've changed this basket. Building again replaces your changes.
              </p>
            )}

            {basketIsStale && !edited && (
              <p className="bb-notice" role="status">
                This basket was built for ${basketBudget?.toFixed(0)}. Build it
                again to use your new budget.
              </p>
            )}
          </div>

          <BasketReceipt
            lines={lines}
            total={total}
            loading={loading}
            budget={basketBudget ?? budget}
            lastChange={lastChange}
            onSelectLine={selectBasketLine}
            onChangeQty={(productId, delta) => {
              const line = lines?.find((item) => item.productId === productId);
              updateLines(
                changeQty(lines ?? [], productId, delta),
                line
                  ? delta > 0
                    ? `Added one more ${line.name}.`
                    : line.qty === 1
                      ? `Removed ${line.name}.`
                      : `Removed one ${line.name}.`
                  : "",
              );
            }}
            onRemove={(productId) => {
              const line = lines?.find((item) => item.productId === productId);
              updateLines(removeLine(lines ?? [], productId), line ? `Removed ${line.name}.` : "");
            }}
            onClear={clearBasket}
            selectedProductId={selectedProduct?.id ?? null}
          />
        </section>

        <section
          id="product-guidance"
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
                inBasketQty={quantityOf(lines, selectedProduct.id)}
                onAdd={addSelectedProduct}
              />

              <SubstituteCard
                productId={selectedProduct.id}
                userId={USER_ID}
                replacing={quantityOf(lines, selectedProduct.id) > 0}
                onUse={applySubstitute}
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
                price signal, and cheaper alternatives. You can add it, or
                a cheaper swap, straight to your basket.
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
