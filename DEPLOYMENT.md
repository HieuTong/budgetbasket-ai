# Deploying BudgetBasket to a real domain

Backend on Render (Docker, free tier, git-connected auto-deploy),
database on Supabase (permanent free Postgres), frontend on Vercel.

**Cost: $0/month** on this setup. See the cost breakdown in chat for the
full table — the only non-monetary cost is Render's free-tier cold start
(30-50s after 15 min idle).

## 1. Push this repo to GitHub

```bash
cd col-optimizer
git init
git add .
git commit -m "Initial scaffold"
gh repo create budgetbasket-ai --public --source=. --push
```

## 2. Domain

Already registered: `budgetbasket.tech`, via the Student Pack's get.tech
offer. Nothing to do here — DNS gets configured in step 7.

## 3. Set up the database (Supabase — permanent free tier)

1. https://supabase.com → New Project.
2. **Project Settings → Database** → copy the connection string (URI
   format, "Connection pooling" version — plays nicer with Render's free
   tier than the direct connection).
3. Keep this handy for step 4.

## 4. Deploy the backend (Render)

1. `render.yaml` is already set to `budgetbasket.tech` — nothing to edit.
2. https://render.com → **New + → Blueprint** → connect your GitHub repo.
   Render reads `render.yaml` automatically.
3. Fill in the two `sync: false` env vars when prompted:
   - `DATABASE_URL` → the Supabase connection string from step 3
   - `GEMINI_API_KEY` → your key (from https://aistudio.google.com/apikey — no
     billing required, free tier)
4. Deploy. You'll get a URL like `budgetbasket-backend.onrender.com`.
   Confirm `/health` returns `{"status": "ok"}` (allow for cold start on
   first hit).
5. **Settings → Custom Domains** → add `api.budgetbasket.tech`, follow
   Render's CNAME instructions — free on Render's plan, no upcharge.

## 5. Load data into Supabase

```bash
cd backend
DATABASE_URL="<your supabase connection string>" python -m seed.load_seed_data
```

Run this from your own machine — connects directly to Supabase, no need
to route through Render for a one-time seed.

## 6. Deploy the frontend (Vercel)

1. https://vercel.com → **New Project** → import the repo → root
   directory `frontend`.
2. Env var: `NEXT_PUBLIC_API_BASE` = `https://api.budgetbasket.tech`.
3. Deploy → **Settings → Domains** → add `budgetbasket.tech` and
   `www.budgetbasket.tech`.

## 7. Point the domain's DNS (get.tech's DNS panel, not Namecheap —

## budgetbasket.tech was registered there)

| Type     | Host  | Value                                            |
| -------- | ----- | ------------------------------------------------ |
| A Record | `@`   | Vercel's IP (from Vercel's domain setup)         |
| CNAME    | `www` | `cname.vercel-dns.com`                           |
| CNAME    | `api` | the Render hostname (from Render's domain setup) |

## 8. Verify end-to-end

- `https://budgetbasket.tech` loads the UI
- `https://api.budgetbasket.tech/health` returns `{"status": "ok"}`
  (first hit may be slow — cold start)
- The budget slider calls the backend and returns an optimized basket

## Ongoing: CI vs CD

`.github/workflows/ci.yml` runs build/import checks on every push (CI).
Actual deployment is handled by Render's and Vercel's own git
integration — both auto-deploy on push to `main` once connected. No
custom Actions deploy step needed.

## If cold starts become a real problem

Render Starter ($7/mo) removes them. Worth it only during weeks you're
actively interviewing and expect people to click the live link cold —
otherwise the free tier is fine.
