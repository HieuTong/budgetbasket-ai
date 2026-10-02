"use client";

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
  return (
    <div className="space-y-4">
      <div className="flex items-baseline justify-between">
        <label
          htmlFor="budget"
          className="font-display text-sm text-ink/70"
        >
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
        onChange={(event) => onChange(Number(event.target.value))}
        className="w-full accent-savings"
        aria-label="Weekly grocery budget"
      />

      <div className="flex justify-between font-mono text-xs text-ink/40">
        <span>${min}</span>
        <span>${max}</span>
      </div>

      <button
        type="button"
        onClick={onOptimize}
        disabled={loading}
        className="w-full rounded-sm bg-ink px-4 py-3 font-mono text-xs font-medium text-paper transition hover:bg-ink/90 disabled:cursor-wait disabled:opacity-50"
      >
        {loading ? "Optimizing…" : "Optimize basket"}
      </button>
    </div>
  );
}
