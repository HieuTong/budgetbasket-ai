"use client";

import { useState } from "react";
import BudgetSlider from "@/components/BudgetSlider";
import BasketReceipt from "@/components/BasketReceipt";
import SwapTips from "@/components/SwapTips";
import AgentChat from "@/components/AgentChat";
import ProductSearch from "@/components/ProductSearch";
import DecisionCard from "@/components/DecisionCard";
import SubstituteCard from "@/components/SubstituteCard";
import {
  optimizeBasket,
  type OptimizeResponse,
  type Product,
} from "@/lib/api";

const USER_ID = 1;

export default function Home() {
  const [budget, setBudget] = useState(85);
  const [basket, setBasket] = useState<OptimizeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);

  async function handleOptimize() {
    setLoading(true);

    try {
      const result = await optimizeBasket(USER_ID, budget);
      setBasket(result);
    } catch {
      setBasket(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto min-h-screen max-w-md px-5 py-10">
      <header className="mb-8">
        <h1 className="font-display text-3xl italic text-ink">
          BudgetBasket
        </h1>

        <p className="mt-1 text-sm text-ink/60">
          Optimize what you already buy, against what you can actually spend.
        </p>
      </header>

      <div className="mb-6 rounded-sm bg-white px-5 py-5 ring-1 ring-line/60">
        <BudgetSlider
          budget={budget}
          onChange={setBudget}
          onOptimize={handleOptimize}
          loading={loading}
        />
      </div>

      <div className="mb-6">
        <BasketReceipt
          basket={basket}
          loading={loading}
          budget={budget}
        />
      </div>

      <div className="mb-6">
        <ProductSearch
          selectedProductId={selectedProduct?.id ?? null}
          onSelect={setSelectedProduct}
        />
      </div>

      <div className="mb-6">
        <DecisionCard
          productId={selectedProduct?.id ?? null}
          userId={USER_ID}
        />
      </div>

      <div className="mb-6">
        <SubstituteCard
          productId={selectedProduct?.id ?? null}
          userId={USER_ID}
        />
      </div>

      <div className="mb-6">
        <SwapTips />
      </div>

      <AgentChat userId={USER_ID} />

      <footer className="mt-10 text-center font-mono text-[11px] text-ink/30">
        prices are indicative — connect a real catalog to go live
      </footer>
    </main>
  );
}