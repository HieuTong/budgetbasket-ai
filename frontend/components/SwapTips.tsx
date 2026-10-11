const TIPS = [
  {
    title: "Same goodness, smaller bill",
    symbol: "↘",
    text: "Home-brand milk saves around $0.70/2L with the same nutrition.",
  },
  {
    title: "Make the freezer your friend",
    symbol: "❄",
    text: "Frozen veg keeps longer and costs 30–50% less per kilo than fresh.",
  },
  {
    title: "Rethink your protein",
    symbol: "↔",
    text: "Canned legumes are a cheaper protein source than red meat.",
  },
];

export default function SwapTips() {
  return (
    <section className="bb-card bb-tips" aria-label="Swaps worth knowing">
      <h2 className="bb-section-title">swaps worth knowing</h2>

      <ul>
        {TIPS.map((tip) => (
          <li key={tip.title}>
            <span className="bb-tip-icon" aria-hidden="true">
              {tip.symbol}
            </span>
            <div>
              <h3>{tip.title}</h3>
              <p>{tip.text}</p>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
