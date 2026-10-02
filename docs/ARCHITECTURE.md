# BudgetBasket AI — Target Architecture

## Purpose
BudgetBasket AI is an uncertainty-aware personal decision platform combining personalized purchase optimization, financial state modeling, probabilistic ML, fraud detection, DecisionOS, LLM tool orchestration, retrieval, and Stripe test-mode integration.

## Core principle
ML predicts. Optimization searches. RAG grounds. LLMs investigate and orchestrate. DecisionOS decides.

## Domain boundaries
Purchase answers what this user should buy and whether buying now is appropriate.
Fraud answers whether a transaction is likely legitimate and what operational action should be taken.
DecisionOS answers which action should be selected from beliefs, actions, outcomes, utility, risk constraints, and available information.
DecisionOS must not depend on grocery, payment, or fraud-specific modules.

## Target backend structure
backend/app/
  api/routes/ — users, finances, products, basket, transactions, decisions, chat
  db/ — models, session, repositories
  decisionos/ — belief, prediction, utility, decision, information
  purchase/ — optimizer, similarity, forecasting
  fraud/ — features, model, calibration, service
  agent/ — agent and tools
  rag/ — knowledge base and retriever
  integrations/ — Open Prices and Stripe

## Purchase flow
User -> financial state + purchase history -> catalog + price history -> personalized utility -> purchase optimizer -> DecisionOS -> purchase decision.

## Fraud flow
Transaction -> feature generation -> fraud probability -> belief state -> DecisionOS -> approve/challenge/review/decline -> outcome -> history.

## Agent flow
User request -> LLM -> structured tool call -> domain service -> evidence -> DecisionOS -> structured decision -> LLM explanation -> user.

## Architectural boundary
The LLM is an orchestrator and natural-language interface. ML models estimate probabilities or forecasts. Optimization algorithms search feasible combinations. DecisionOS performs authoritative action selection from structured inputs. RAG provides grounded reference information but does not override structured financial or risk calculations.