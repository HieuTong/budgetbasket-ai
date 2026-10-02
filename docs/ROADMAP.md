# BudgetBasket AI Revamp — Complete Project Plan

## Vision
BudgetBasket AI will evolve from a grocery-budget optimizer into an uncertainty-aware personal decision platform.

Core principle: ML predicts. Optimization searches. RAG grounds. LLMs investigate and orchestrate. DecisionOS decides.

The user-facing product remains BudgetBasket AI. DecisionOS is the reusable internal decision layer. Two application modules demonstrate the same framework: personalized purchase decisions and card/payment fraud-risk decisions.

Every phase must be implemented, tested, verified, documented, and recorded in docs/IMPLEMENTATION_LOG.md before it is considered complete.

## Phase 0 — Baseline, Branching, and Engineering Record
Objective: create a safe revamp branch and durable project memory independent of chat history.
Work: create revamp/decisionos from main; document current architecture and gaps; add ROADMAP.md, ARCHITECTURE.md, DECISIONOS.md, and IMPLEMENTATION_LOG.md; define phase completion rules; preserve main as baseline.
Completion: branch exists; documentation is self-contained; current limitations are recorded; another developer or LLM can continue without this chat.

## Phase 1 — Make BudgetBasket Data-Driven
Objective: remove hardcoded product candidates and connect PostgreSQL data to the real application.
Current problems: basket optimization uses hardcoded products; chat uses hardcoded candidates; user_id is not meaningfully used; purchase-history tooling is a stub; purchase API lacks useful product context.
Work: create repository/service layers for products, purchases, and price history; query the real catalog; implement purchase-history retrieval; derive a first deterministic personalized utility from purchase frequency, recency, quantity preference, category preference, and similarity; replace hardcoded basket candidates; give the agent real catalog/history context; replace permanent frontend USER_ID=1 architecture with explicit demo-user/session handling.
Tests: repositories, empty history, unknown user, product retrieval, utility scoring, optimizer constraints, zero/negative budgets, insufficient candidates.
Completion: a user with purchase history receives a basket derived from that history and the real catalog. No production route depends on the old hardcoded five-product list.

## Phase 2 — Personal Financial State
Objective: make decisions depend on the user's broader financial situation, not only a grocery budget.
Add domain concepts for financial profile, accounts/balance, income, recurring and one-off expenses, obligations, goals, and minimum safety reserve.
Represent decision state conceptually as S_t=(B_t,I_t,E_t,O_t,G_t,H_t,P_t): balance, expected income, essential expenses, obligations, goals, history, preferences.
Work: database models/migrations; repositories; API endpoints; validation; deterministic cash-flow projection; available discretionary amount; projected reserve after a purchase.
Completion: the system can calculate current resources, upcoming essential commitments, protected reserve, and discretionary spending under explicit assumptions.

## Phase 3 — DecisionOS Core
Objective: build a domain-independent uncertainty-aware decision engine.
DecisionOS must not import grocery, Stripe, or fraud-specific logic. It understands belief states, actions, outcomes, utility, risk, and information.
Core interface concept: engine.decide(belief_state, actions, outcome_model, utility_model, risk_model).
Expected utility: EU(a)=sum over states of P(state|evidence)*U(a,state). Select the action maximizing expected utility subject to configured risk constraints.
Work: typed domain objects; expected utility calculation; deterministic action selection; risk constraints; structured DecisionResult containing selected action, action scores, probabilities, constraints, and reasons; comprehensive unit tests.
Completion: DecisionOS solves generic toy decisions without knowing anything about groceries or fraud.

## Phase 4 — Uncertainty-Aware Purchase Decisions
Objective: connect purchasing to DecisionOS.
Actions: BUY_NOW, WAIT, BUY_SUBSTITUTE, BUY_SMALLER_QUANTITY, SKIP.
Represent uncertainty around future price, income timing, essential expenses, availability, and expected usefulness.
Work: convert forecasts into scenarios/distributions; estimate action consequences; calculate expected utility; enforce reserve constraints; produce auditable decision records and explanations.
Completion: the system distinguishes which basket is optimal from whether the user should purchase it now.

## Phase 5 — Purchase Optimization 2.0
Objective: strengthen the existing PuLP optimizer as a domain component underneath DecisionOS.
Keep PuLP/CBC integer optimization. Improve candidate generation, quantity preferences, min/max quantities, substitutions, category constraints where supported, price scenarios, forecasting, historical-price comparison, and optimization diagnostics.
Architecture: DecisionOS decides whether/how much spending is appropriate; the purchase optimizer decides which combination of products satisfies the constraints.
Completion: purchase optimization is reproducible, constrained, personalized, and cleanly separated from DecisionOS.

## Phase 6 — Fraud Detection ML
Objective: add a real transaction-risk prediction model.
Add Transaction fields such as amount, merchant, timestamp, location, device, and payment method. Engineer features including amount deviation, merchant novelty, device novelty, geographic deviation, velocity, failed attempts, merchant risk, and historical behavior.
Use a public fraud dataset for reproducible model development. Keep training data, demo transactions, and Stripe sandbox transactions conceptually separate.
Start with a logistic-regression baseline, then add a tree/boosting model if justified. Handle class imbalance explicitly.
Evaluate ROC-AUC, PR-AUC, precision, recall, F1, Brier score, log loss, and calibration.
Completion: a documented, versioned, calibrated model produces P(fraud|X).

## Phase 7 — Fraud DecisionOS
Objective: turn fraud probability into an explicit action under asymmetric costs.
Actions: APPROVE, CHALLENGE, HUMAN_REVIEW, DECLINE.
Work: define outcome utilities/costs; calculate expected utility for every action; apply operational constraints; record decision reasoning; compare against a fixed-threshold baseline.
Principle: P(fraud|X) is an input to decision-making, not the decision itself.
Completion: identical model probabilities can lead to different actions when costs, policy, or user context differ.

## Phase 8 — Bayesian Updating
Objective: implement explicit belief updating from sequential evidence.
Work: define priors; define evidence likelihoods; implement posterior updates; support multiple evidence updates; log prior, evidence, likelihood, and posterior; test against hand-calculated examples.
Bayesian relationship: P(H|E)=P(E|H)P(H)/P(E).
Completion: the system updates beliefs as evidence arrives rather than treating every prediction as a final immutable probability.

## Phase 9 — Value of Information
Objective: make information gathering itself part of decision-making.
VOI = EU(best action after information) - EU(best action now) - information cost.
Potential information sources: authentication, device history, merchant history, recent transactions, location history, additional customer context.
Work: model possible information outcomes; estimate expected value; include friction/cost; choose between deciding now and gathering information.
Completion: the system can explicitly justify an additional investigation step when its expected value exceeds its cost.

## Phase 10 — LLM Agent Redesign
Objective: turn the LLM into an investigator/orchestrator rather than the authoritative decision-maker.
Responsibilities: interpret natural language, extract structured intent, select tools, gather evidence, identify missing information, call DecisionOS, explain structured results.
Potential tools: get_customer_profile, get_financial_state, get_purchase_history, get_product_catalog, get_product_prices, get_price_forecast, get_recent_transactions, get_device_history, get_merchant_history, run_fraud_model, request_authentication, run_decision_engine.
Guardrails: typed tool contracts, step limits, validation, timeouts, retries, no direct financial decision calculation by the LLM, deterministic DecisionOS remains authoritative.
Completion: the agent can orchestrate an investigation while DecisionOS produces the numerical decision.

## Phase 11 — Agent Investigation Loop
Objective: combine agentic investigation, Bayesian updating, and VOI.
Target loop: OBSERVE -> ESTIMATE -> CHECK UNCERTAINTY -> VOI -> TOOL -> UPDATE BELIEF -> DECIDE -> ACT.
Work: create decision context; allow evidence requests; feed evidence to belief updater; recalculate VOI; stop when the decision is stable, useful information is exhausted, the step limit is reached, or immediate action is required; record every step.
Completion: a suspicious transaction can trigger additional investigation before the final action.

## Phase 12 — Stripe Sandbox Integration
Objective: connect payment flow to realistic test infrastructure without handling real card data.
Work: Stripe test-mode integration; PaymentIntent/Checkout; webhook handling and signature verification; transaction persistence; fraud scoring; DecisionOS decision; simulated challenge outcomes.
Boundary: Stripe handles payment processing; BudgetBasket/DecisionOS handles application-level risk decisioning. Never store raw card details.
Completion: a complete test transaction flows through payment creation, risk evaluation, decisioning, and state update.

## Phase 13 — Sequential Decision and Learning Loop
Objective: make the system stateful over time.
Flow: action -> outcome -> new state -> next decision.
Work: update financial, purchase, and fraud history; record outcomes; create features from prior outcomes; explore sequential decision concepts; document where the implementation approximates MDP/POMDP ideas.
Completion: future decisions can use consequences and history from previous decisions.

## Phase 14 — Evaluation Framework
Objective: create reproducible experiments showing what each component contributes.
Purchase metrics: budget violations, total cost, purchase utility, cost savings, personalization, reserve violations, forecast error.
Fraud metrics: precision, recall, F1, ROC-AUC, PR-AUC, false-positive rate, legitimate decline rate.
Decision metrics: expected financial loss, expected utility, fraud prevented, challenge rate, false declines, customer friction, investigation/tool-call cost.
Probability metrics: Brier score, log loss, calibration.
Completion: important claims are backed by experiments or clearly labelled as design goals.

## Phase 15 — Baseline Experiments
Objective: compare progressively richer decision systems under identical scenarios.
Baseline A: rule-based. Baseline B: ML plus fixed threshold. System C: ML plus DecisionOS. System D: ML plus DecisionOS plus Bayesian updating plus agentic investigation plus VOI.
Work: fixed scenario sets; identical cases through every system; saved results; tables/plots; analysis of trade-offs.
Completion: repository contains reproducible evidence about the effects of architectural choices.

## Phase 16 — Observability and Auditability
Objective: make historical decisions inspectable.
Record decision ID, timestamp, user ID, model version, feature version, belief state, evidence, candidate actions, expected utilities, constraints, selected action, agent tool calls, VOI calculations, and latency.
Work: structured logs, correlation IDs, model-version tracking, safe error logging, audit records, sensitive-data minimization.
Completion: a developer can reconstruct why a historical decision was made without depending on an LLM transcript.

## Phase 17 — Production Engineering
Objective: make the project credible as a production-oriented software system.
Backend: FastAPI, SQLAlchemy, PostgreSQL, Pydantic, service/repository boundaries, dependency injection, error handling.
ML: reproducible training, model artifact/versioning strategy, feature pipeline, calibration, evaluation scripts.
Agent: typed tools, retries, timeouts, step limits, structured outputs, deterministic fallback behavior.
Testing: unit, integration, API, database, ML, DecisionOS, and agent-tool tests.
CI/CD: linting, tests, build, security checks where practical, deployment verification.

## Phase 18 — Security and Privacy
Objective: treat financial and transaction data as sensitive.
Work: authentication, authorization, user isolation, secret management, webhook verification, input validation, rate limiting where appropriate, no raw card storage, test-mode payment data, audit logging, data minimization.
Completion: security assumptions and limitations are explicitly documented.

## Phase 19 — Frontend Redesign
Objective: build a UI that demonstrates decisions instead of merely exposing a chatbot.
Screens/components: financial overview; purchase decision; transaction activity; agent investigation.
Financial overview: balance, upcoming expenses, expected income, reserve, goals.
Purchase view: budget, basket, expected cost, utility, reserve risk, price uncertainty.
Transaction view: recent transactions, fraud probability, action, challenge status.
Completion: the UI communicates the system architecture and decision outputs clearly.

## Phase 20 — Decision Explanation
Objective: make explanations understandable without allowing the LLM to invent reasons.
Generate explanations from structured decision data: probabilities, evidence, utilities, constraints, and selected action.
The LLM may turn structured facts into natural language, but must not invent numerical facts.
Explanation structure: Decision -> Evidence -> Trade-offs -> Constraints -> Action.
Completion: every displayed explanation is traceable to structured system output.

## Phase 21 — Documentation and Technical Write-Up
Objective: make the repository independently understandable.
README: problem, motivation, architecture, DecisionOS, purchase optimization, fraud ML, Bayesian updating, VOI, agent, Stripe, evaluation, deployment, limitations.
Architecture documentation: components, data flow, interfaces, database, ML pipeline, agent loop.
DecisionOS documentation: mathematical formulation, assumptions, examples, limitations.
Evaluation documentation: datasets, baselines, metrics, results, interpretation.
Completion: another engineer or LLM can understand and operate the project without this conversation.

## Phase 22 — Portfolio and Interview Packaging
Objective: present the project for AI Engineer, ML Engineer, and Software Engineer roles.
GitHub deliverables: clean README, architecture diagrams, demo instructions, tests, evaluation results, design decisions, limitations, meaningful commit history.
Resume topics: decision engine, uncertainty modeling, fraud ML, optimization, agentic orchestration, RAG, cloud/backend, Stripe sandbox, evaluation.
Interview topics: probability estimation, calibration, Bayesian updating, fraud imbalance, forecasting, tool calling, VOI, guardrails, FastAPI, PostgreSQL, event flow, webhooks, scalability, observability, security, failure modes.

## Rules for Every Phase
1. Do not break main.
2. Work on revamp/decisionos until changes are intentionally ready for merge.
3. Prefer small coherent commits.
4. Record architectural decisions and reasons.
5. Do not add an LLM where deterministic logic is more appropriate.
6. Do not let the LLM become the authoritative numerical decision-maker.
7. Keep DecisionOS domain-independent.
8. Distinguish ML predictions from business decisions.
9. Prefer reproducible experiments over qualitative claims.
10. Record assumptions and limitations.
11. Add tests as functionality is introduced.
12. Update IMPLEMENTATION_LOG.md after every completed phase.
13. Every phase log must include completed work, files changed, tests, verification, decisions, limitations, deferred work, and next phase.
14. Treat repository documentation as the source of truth when chat history is unavailable.

## Current State
Phase 0: In progress. The revamp/decisionos branch has been created from main. The repository baseline has been inspected and the major architecture gaps have been identified.
Next action: commit the durable project documentation, then implement Phase 1.