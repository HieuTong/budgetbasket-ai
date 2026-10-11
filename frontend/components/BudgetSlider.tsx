"use client";

import { useId } from "react";

type Props = {
  budget: number;
  onChange: (value: number) => void;
  onOptimize: () => void;
  loading?: boolean;
  min?: number;
  max?: number;
};

export default function BudgetSlider({
  budget,
  onChange,
  onOptimize,
  loading = false,
  min = 30,
  max = 200,
}: Props) {
  const id = useId();

  return (
    <div>
      <div className="bb-section-heading">
        <label htmlFor={id} className="bb-section-title">
          weekly budget
        </label>
        <span className="bb-micro">$5 steps</span>
      </div>

      <div className="bb-budget-value">
        <output htmlFor={id}>${budget.toFixed(0)}</output>
        <span>/ week</span>
      </div>

      <input
        id={id}
        className="bb-range"
        type="range"
        min={min}
        max={max}
        step={5}
        value={budget}
        disabled={loading}
        onChange={(event) => onChange(Number(event.target.value))}
        aria-label="Weekly grocery budget"
        aria-valuetext={`${budget} dollars per week`}
      />

      <div className="bb-range-limits">
        <span>${min}</span>
        <span>${max}</span>
      </div>

      <button
        className="bb-button bb-button-wide"
        type="button"
        onClick={onOptimize}
        disabled={loading}
      >
        <span aria-hidden="true">✧</span>
        {loading ? "Optimizing…" : "Optimize basket"}
      </button>
    </div>
  );
}
