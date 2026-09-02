"use client";

type Props = {
  budget: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
};

export default function BudgetSlider({ budget, onChange, min = 30, max = 200 }: Props) {
  return (
    <div className="space-y-2">
      <div className="flex items-baseline justify-between">
        <label htmlFor="budget" className="font-display text-sm text-ink/70">
          Weekly budget
        </label>
        <span className="font-mono text-2xl font-medium text-savings">
          ${budget.toFixed(0)}
        </span>
      </div>
      <input
        id="budget"
        type="range"
        min={min}
        max={max}
        step={5}
        value={budget}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-savings"
        aria-label="Weekly grocery budget"
      />
      <div className="flex justify-between font-mono text-xs text-ink/40">
        <span>${min}</span>
        <span>${max}</span>
      </div>
    </div>
  );
}
