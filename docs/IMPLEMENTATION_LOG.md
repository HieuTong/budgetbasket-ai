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
Status: In progress

### Completed so far
- Added SQLAlchemy repository layers for products, purchases, and price history.
- Added a deterministic personalized-utility service using purchase frequency, recency, quantity behavior, and category affinity.
- Added a Product <-> Purchase ORM relationship.
- Replaced the basket route's hardcoded five-product list with the database catalog and user purchase history.
- Added candidate count and purchase-history count to the basket response for observability during the migration.
- Expanded purchase API responses with product name, category, and current unit price.
- Connected the purchase-history agent tool to the purchase repository.
- Updated the chat route to build agent context from the real catalog and the user's purchase history.
- Updated agent conversion logic so catalog dictionaries can be converted into the similarity Product type.
- Added personalization unit tests.

### Files added
- backend/app/db/repositories/products.py
- backend/app/db/repositories/purchases.py
- backend/app/db/repositories/price_history.py
- backend/app/db/repositories/__init__.py
- backend/app/services/personalization.py
- backend/app/services/__init__.py
- backend/tests/test_personalization.py

### Files changed
- backend/app/db/models.py
- backend/app/api/routes/basket.py
- backend/app/api/routes/purchases.py
- backend/app/api/routes/chat.py
- backend/app/agent/agent.py
- backend/app/agent/tools.py

### Verification
- Existing repository tests remain present.
- New personalization tests were added.
- GitHub Actions verification has not yet been run against the revamp branch because the existing workflow triggers on pushes to main or pull requests targeting main.

### Architectural decisions
- The first personalization model is deterministic and explainable; ML personalization is deferred until there is enough real user data to justify it.
- The basket optimizer consumes domain candidates generated from the database rather than owning database access.
- Repository/service boundaries are introduced before the DecisionOS layer so future decision logic does not become coupled to SQLAlchemy.

### Known limitations
- New users without purchase history receive neutral utility, so the optimizer has limited personalization for cold-start users.
- Current candidate generation uses all positively priced catalog products; richer constraints and candidate selection are deferred to Phase 5.
- Current price forecasting is not yet integrated into basket decisions.
- No authentication/session system exists yet.
- Automated CI verification is pending.

### Next
- Run Phase 1 through CI.
- Fix any failures.
- Complete cold-start/edge-case tests.
- Then mark Phase 1 complete and begin Phase 2 (Personal Financial State).

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