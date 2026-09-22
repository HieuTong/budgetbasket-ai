# Implementation Log

This file is the durable project memory for the BudgetBasket AI revamp. Do not rely on chat history for project state.

## Phase 0 — Baseline, Branching, and Engineering Record
Status: In progress

### Completed
- Created revamp/decisionos from main.
- Inspected the existing BudgetBasket architecture.
- Identified hardcoded product candidates in the basket route.
- Identified hardcoded candidates and empty product context in the chat route.
- Identified the purchase-history agent tool stub.
- Identified the existing Product, PriceHistory, and Purchase database foundation.
- Defined the complete multi-phase revamp roadmap.
- Defined the domain-independent DecisionOS boundary.
- Defined the purchase and fraud application modules.
- Defined the LLM/DecisionOS responsibility boundary.

### Architectural decisions
1. BudgetBasket remains the user-facing product.
2. DecisionOS is an internal reusable decision engine.
3. Purchase optimization and fraud detection are separate domain modules.
4. DecisionOS must not depend on grocery, Stripe, or fraud-specific code.
5. ML produces predictions/probabilities; it does not automatically select business actions.
6. The LLM is an investigator/orchestrator and explanation layer, not the authoritative numerical decision-maker.
7. Stripe will be test-mode only.
8. Every phase must leave a durable record here.

### Known baseline limitations
- Basket route uses hardcoded candidate products.
- Chat route uses hardcoded candidates.
- Purchase history is not connected to the agent tool.
- user_id is not yet used to personalize optimization.
- Purchase responses need richer product information.
- Current price forecasting is simple linear trend regression and does not capture cyclical produce pricing well.
- Existing RAG knowledge is generic advice and should not become the source of authoritative financial decisions.
- Existing frontend uses a hardcoded demo user ID.

### Verification
- Repository baseline inspected.
- Revamp branch created from main.

### Next
Complete Phase 0 documentation commit, then begin Phase 1: data-driven catalog, purchase history, personalized utility, and optimizer integration.

## Phase 1 — Data-Driven BudgetBasket
Status: Not started

## Phase 2 — Personal Financial State
Status: Not started

## Phase 3 — DecisionOS Core
Status: Not started

## Phase 4 — Uncertainty-Aware Purchase Decisions
Status: Not started

## Phase 5 — Purchase Optimization 2.0
Status: Not started

## Phase 6 — Fraud Detection ML
Status: Not started

## Phase 7 — Fraud DecisionOS
Status: Not started

## Phase 8 — Bayesian Updating
Status: Not started

## Phase 9 — Value of Information
Status: Not started

## Phase 10 — LLM Agent Redesign
Status: Not started

## Phase 11 — Agent Investigation Loop
Status: Not started

## Phase 12 — Stripe Sandbox Integration
Status: Not started

## Phase 13 — Sequential Decision and Learning Loop
Status: Not started

## Phase 14 — Evaluation Framework
Status: Not started

## Phase 15 — Baseline Experiments
Status: Not started

## Phase 16 — Observability and Auditability
Status: Not started

## Phase 17 — Production Engineering
Status: Not started

## Phase 18 — Security and Privacy
Status: Not started

## Phase 19 — Frontend Redesign
Status: Not started

## Phase 20 — Decision Explanation
Status: Not started

## Phase 21 — Documentation and Technical Write-Up
Status: Not started

## Phase 22 — Portfolio and Interview Packaging
Status: Not started