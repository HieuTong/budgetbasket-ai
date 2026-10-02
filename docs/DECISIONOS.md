# DecisionOS — Design Specification

## Purpose
DecisionOS is the reusable mathematical decision layer of BudgetBasket AI.

It is not an LLM, chatbot, grocery optimizer, fraud classifier, or payment processor.

It is a domain-independent engine for choosing actions under uncertainty.

## Conceptual pipeline
What do I know? -> What might actually be happening? -> What can I do? -> What could happen after each action? -> How valuable or costly is each outcome? -> What risks must be respected? -> What action should be taken?

## Core interface
Conceptually: engine.decide(belief_state, actions, outcome_model, utility_model, risk_model).

## Expected utility
For action a: EU(a) = sum over possible states s of P(s | evidence) * U(a, s).
Select a* = argmax EU(a), subject to configured risk constraints.

## Belief state
A belief state contains uncertain hypotheses and their probabilities. Example: fraud=0.35, legitimate=0.65.

## Bayesian updating
When new evidence arrives, update using P(H|E)=P(E|H)P(H)/P(E). Preserve prior, evidence, likelihood, and posterior so the process is auditable.

## Risk
Expected utility alone may be insufficient when downside risk is asymmetric. A financial example is P(balance_after < minimum_reserve) < epsilon.

## Value of information
VOI = EU(best action after information) - EU(best action now) - information cost.
If VOI is positive and operationally feasible, the system may gather more information before acting.

## Domain adapters
Purchase and fraud modules provide belief state, actions, outcome model, utility model, and risk constraints. DecisionOS returns a generic decision.

## LLM boundary
The LLM can interpret requests, select tools, investigate, and explain decisions. It must not replace the authoritative DecisionOS calculation.

## Auditability
A decision result should retain decision ID, probabilities, evidence, candidate actions, expected utility, constraints, selected action, model/version information, and information-gathering steps.