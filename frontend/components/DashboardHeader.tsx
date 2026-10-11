"use client";

import { useEffect, useState } from "react";

type Props = {
  totalCost: number | null;
  budget: number;
  stale?: boolean;
};

function formatCurrentWeek() {
  const monday = new Date();
  monday.setHours(12, 0, 0, 0);

  const daysSinceMonday = (monday.getDay() + 6) % 7;
  monday.setDate(monday.getDate() - daysSinceMonday);

  const sunday = new Date(monday);
  sunday.setDate(monday.getDate() + 6);

  const formatter = new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
  });

  return `${formatter.format(monday)} – ${formatter.format(sunday)}, ${sunday.getFullYear()}`;
}

export default function DashboardHeader({
  totalCost,
  budget,
  stale = false,
}: Props) {
  const [week, setWeek] = useState("This week");

  useEffect(() => {
    setWeek(formatCurrentWeek());
  }, []);

  const status =
    totalCost === null
      ? "Ready to plan"
      : stale
        ? "Budget changed"
        : totalCost <= budget
          ? "Within budget"
          : "Over budget";

  const overBudget =
    totalCost !== null && !stale && totalCost > budget;

  return (
    <header>
      <a href="#main-content" className="bb-skip-link">
        Skip to dashboard
      </a>

      <div className="bb-topbar">
        <a href="/" className="bb-brand" aria-label="BudgetBasket home">
          <span className="bb-brand-mark" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none">
              <path
                d="m8 10 4-6 4 6M4 10h16l-2 10H6L4 10Zm5 4v3m6-3v3"
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </span>
          <span>BudgetBasket</span>
          <span className="bb-brand-ai">AI</span>
        </a>

        <nav className="bb-nav" aria-label="Main navigation">
          <a href="#main-content" aria-current="page">
            My basket
          </a>
        </nav>

        <span className="bb-profile-label">Your weekly shop</span>
      </div>

      <div className="bb-intro">
        <div>
          <h1>Good groceries. Better numbers.</h1>
          <p>
            Your weekly shop, with a little intelligence in every aisle.
          </p>
        </div>

        <div className="bb-week-info">
          <span
            className={`bb-status${overBudget ? " bb-status-warning" : ""}`}
            role="status"
          >
            <span aria-hidden="true" />
            {status}
          </span>
          <span className="bb-week">{week}</span>
        </div>
      </div>
    </header>
  );
}
