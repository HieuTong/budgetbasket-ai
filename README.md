# BudgetBasket AI

A cost-of-living optimizer for Australian households: given your usual purchases and a
budget, it builds a shopping basket that stays close to your habits while cutting cost —
using classical ML, retrieval-augmented generation, and an agentic tool-calling layer,
not just a single LLM prompt.

## Why this project

Grocery prices in Australia have risen sharply, and most "AI shopping" demos are thin
wrappers around a chat prompt. This project is built to show the opposite: a **real
optimization algorithm** at the core, with ML and LLM components layered around it where
they're actually the right tool — not used everywhere for effect.

## Architecture

```
                     ┌─────────────────┐
                     │   Next.js UI     │
                     └────────┬─────────┘
                              │
                     ┌────────▼─────────┐
                     │   FastAPI backend │
                     └───┬───────┬──────┘
           ┌─────────────┘       └─────────────┐
   ┌───────▼────────┐                  ┌────────▼────────┐
   │  Classical ML    │                  │   Agent layer    │
   │ ─────────────── │                  │ ──────────────── │
   │ • Similarity      │                  │ Tool-calling loop │
   │   (TF-IDF/cosine) │                  │ over: optimizer,  │
   │ • Price forecast   │                  │ similarity, RAG   │
   │   (trend/slope)    │                  └────────┬────────┘
   │ • Budget optimizer │                            │
   │   (LP / knapsack)  │                   ┌────────▼────────┐
   └────────────────────┘                   │   RAG retriever   │
                                             │ (FAISS + fallback) │
                                             └────────────────────┘
```

## Why Gemini, not OpenAI

Google's Gemini API has a genuine free tier (1,500 requests/day on Flash,
no billing method required) as of 2026 — OpenAI's API doesn't reliably
offer one anymore (small trial credits, if issued at all, expire in 3
months and typically still require adding a card). Function calling is
done manually here (JSON-schema tool declarations, parsed
`function_call` parts) rather than via the SDK's automatic
function-calling feature, to keep the agent's control flow explicit —
see the docstring in `app/agent/agent.py`.

## Why an LP solver, not just an LLM

The budget-fitting problem is a textbook **0/1 knapsack / integer program**: maximize a
utility score subject to a budget constraint. Solving it with PuLP (CBC solver) guarantees
an optimal, budget-respecting basket every time — an LLM asked to do this arithmetic
directly will happily produce a basket that's over budget or leaves money needlessly
unspent. The agent layer *calls* this solver as a tool rather than re-implementing the
math itself.

## Components

| Layer | Technique | File |
|---|---|---|
| Similarity / substitutes | TF-IDF + cosine similarity | `app/ml/similarity.py` |
| Price trend | Linear regression on price history | `app/ml/forecasting.py` |
| Budget optimization | Integer linear programming (PuLP) | `app/ml/optimizer.py` |
| RAG | FAISS + Gemini embeddings, keyword fallback | `app/rag/retriever.py` |
| Agent | Hand-rolled tool-calling loop | `app/agent/agent.py` |

## Data

Two data sources, used deliberately for different purposes:

- **`app/integrations/open_prices_client.py`** — a real client for
  [Open Food Facts' Open Prices API](https://prices.openfoodfacts.org), an
  open, community-sourced grocery price database (ODbL licensed) with
  Australian entries. This is genuine external data. It requires normal
  outbound internet and isn't wired into the seed pipeline by default —
  it's the intended source once deployed to a real server.
- **`seed/products_seed.csv` + `seed/generate_price_history.py`** — 55
  common Australian grocery items with indicative (not live-scraped) unit
  prices, plus synthetic price history generated from documented real
  patterns (fresh produce oscillates roughly every 2 weeks; packaged
  staples drift slowly — see
  [tjhowse/aus_grocery_price_database](https://github.com/tjhowse/aus_grocery_price_database)
  for real-world evidence of this pattern). This is what makes the demo
  runnable immediately without external API access.

Load the seed data:
```bash
cd backend
python -m seed.load_seed_data
```

Known limitation worth fixing before a real demo: the linear-regression
price forecaster in `app/ml/forecasting.py` averages out the ~2-week
oscillation in produce prices rather than detecting it — it reports
"stable" with low confidence on a cyclical item like bananas, which is
honest but not useful. Seasonal decomposition or a simple Fourier term
would fix this; noted in the roadmap below.

## Running locally

```bash
cd backend
cp .env.example .env   # fill in DATABASE_URL and GEMINI_API_KEY
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Visit `http://localhost:8000/docs` for the interactive API.

## Deployment

- **Backend**: containerized (`backend/Dockerfile`) — deployed to Render
  (free tier, git-connected auto-deploy). See `DEPLOYMENT.md` for the full walkthrough.
- **Database**: Supabase — permanent free Postgres tier.
- **Frontend**: Next.js on Vercel.
- **CI**: GitHub Actions (`.github/workflows/ci.yml`) runs an import sanity check and
  Docker build on every push.

## Roadmap

- Swap TF-IDF similarity for sentence-transformer embeddings once catalog size justifies it
- Replace linear-regression forecasting with seasonal decomposition or Prophet, so cyclical produce pricing is actually detected
- Wire `open_prices_client.py` into a scheduled job once deployed, to gradually replace synthetic history with real contributed AU price data
- Wire real purchase history from Postgres into the optimizer's utility scoring
- Add pytest coverage for the optimizer and retriever
