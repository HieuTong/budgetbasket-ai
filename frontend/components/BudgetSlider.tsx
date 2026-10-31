"use client";

import { useId } from "react";

// Common weekly budgets, one tap away.
const PRESETS = [60, 85, 120];

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

      <div className="bb-presets" role="group" aria-label="Quick budgets">
        {PRESETS.map((value) => (
          <button
            key={value}
            type="button"
            aria-pressed={budget === value}
            disabled={loading}
            onClick={() => onChange(value)}
          >
            ${value}
          </button>
        ))}
      </div>

      <button
        className="bb-button bb-button-wide"
        type="button"
        onClick={onOptimize}
        disabled={loading}
      >
        <span aria-hidden="true">✧</span>
        {loading ? "Building your basket…" : `Build my $${budget} basket`}
      </button>
    </div>
  );
}
