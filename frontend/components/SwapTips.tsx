const STATIC_TIPS = [
  "Home-brand milk saves around $0.70/2L with the same nutrition.",
  "Frozen veg keeps longer and costs 30–50% less per kilo than fresh.",
  "Canned legumes are a cheaper protein source than red meat.",
];

export default function SwapTips() {
  return (
    <div className="rounded-sm bg-savings-dim px-5 py-4">
      <p className="font-display text-xs italic text-ink/60">swaps worth knowing</p>
      <ul className="mt-2 space-y-1.5">
        {STATIC_TIPS.map((tip) => (
          <li key={tip} className="flex gap-2 text-sm text-ink/80">
            <span className="text-savings">→</span>
            <span>{tip}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
