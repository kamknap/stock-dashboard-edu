# Stock Dashboard (educational)

A web app for **educational** stock-market analysis with a small analytical
chat. **This is a learning tool — not a trading bot and not investment
advice.** Every surface that shows analysis must display the disclaimer:
*"Educational tool, not investment advice."*

The app is **read-only / analytical**. It does **not** integrate any brokerage
or order-execution API.

## What it does

1. **Scheduled reports** — twice a day (09:00 and 15:00 Europe/Warsaw) the
   backend computes technical indicators for a configurable watchlist,
   generates a market-context report, and stores it. The frontend displays it.
2. **Analytical chat** — you name a company/ticker; the agent fetches current
   data and indicators, checks fresh news, and returns concise context and
   risks. **No binary buy/sell verdict.**
3. **Top movers** — biggest percentage gainers/losers from our own watchlist,
   with a configurable window (daily and weekly). Computed from watchlist data,
   no extra market endpoint.

## Architecture principles

- All **numbers** (indicators, % change, signals, movers ranking) are computed
  **deterministically in Python** (indicators hand-computed in pandas:
  SMA/EMA/RSI/MACD). They are the source of truth.
- The **LLM is narrative only**: it receives already-computed indicators + news
  and describes context and risks. It never guesses price direction.
- **Signals are explicit rules** (e.g. `RSI < 30 AND price > EMA50` =
  "oversold in an uptrend"), not model opinion.
- The same data-fetch and indicator code powers the scheduled reports, the chat
  tool, and the Top movers ranking.
- LLM output is always **validated JSON** (Pydantic) with error handling and a
  fallback when grounding/model fails.

## Repository layout (monorepo)

```
stock-dashboard-edu/
├── api/        # Python + FastAPI backend (Docker, deployed to Render)
├── web/        # React + Vite frontend (Firebase Hosting)  [added in phase 7]
├── render.yaml # Render Blueprint for the backend service
└── README.md
```

## Stack (free tiers)

| Concern        | Choice                                                        |
| -------------- | ------------------------------------------------------------- |
| Frontend       | React + Vite, Recharts, Firebase Hosting                      |
| Backend        | Python + FastAPI, Docker                                      |
| Backend host   | **Render (free)** — container; sleeps when idle (cold start)  |
| Market data    | Yahoo Finance chart endpoint (keyless) — OHLC + price, all tickers |
| News           | Gemini Google Search grounding (report + chat)                |
| LLM            | Gemini Flash via Google AI Studio + Google Search grounding   |
| Database       | Firestore                                                     |
| Scheduler      | GitHub Actions cron -> protected `/run-analysis` endpoint     |
| CI/CD          | GitHub Actions (separate pipelines for web and api)           |

> **Render free note:** the instance spins down after ~15 min of inactivity, so
> the first scheduled call (09:00 / 15:00) triggers a cold start (~30-60 s).
> This is acceptable for a twice-daily job. The same `Dockerfile` also runs on
> Cloud Run unchanged if you switch hosts later.

## Backend — quick start (phase 1)

```bash
cd api
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                                 # then edit values
uvicorn app.main:app --reload --port 8080
# docs at http://localhost:8080/docs
pytest
```

### Endpoints (phase 1 = stubs)

| Method | Path            | Notes                                                       |
| ------ | --------------- | ----------------------------------------------------------- |
| GET    | `/health`       | Liveness/readiness probe.                                   |
| GET    | `/`             | Service info.                                               |
| POST   | `/run-analysis` | Protected by `X-Scheduler-Secret` header. Scheduler only.   |
| POST   | `/chat`         | Accepts conversation history; returns context + disclaimer. |
| GET    | `/watchlist`    | The configured watchlist (symbol, name, market, currency).  |
| GET    | `/market/{symbol}` | Snapshot: price + deterministic daily % change. Watchlist symbols only. |
| GET    | `/market/{symbol}/candles` | Daily OHLCV series (defaults: range=6mo, interval=1d).      |
| GET    | `/market/{symbol}/analysis` | Snapshot + indicators (SMA/EMA/RSI/MACD) + rule-based signals. |
| GET    | `/top-movers`   | Gainers/losers from the watchlist, daily and weekly windows. |

### Data sources

Finnhub's free tier turned out to expose only real-time `/quote` for US tickers
(`/stock/candle` is premium; non-US returns 403), so it cannot feed the
indicators. The app uses the **Yahoo Finance chart endpoint** (keyless) as the
single source of truth for OHLC + price across all tickers, including Samsung
(KRW) and KGHM (PLN). News comes from Gemini's Google Search grounding.

> Note: Yahoo's chart endpoint is unofficial (the same one `yfinance` wraps).
> It is used here for a non-commercial, educational project, with aggressive
> caching and a low request volume (two batch runs/day + cached chat).

## Secrets

Secrets are **never** committed. Store them as environment variables locally
(`api/.env`, git-ignored) and as **GitHub Secrets** / **Render environment
variables** in deployment. See `api/.env.example` for the full list. Generate
the scheduler secret with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Roadmap

1. ✅ Repo structure + FastAPI skeleton (`/health`, `/run-analysis`, `/chat` stubs) + Dockerfile + requirements.
2. ✅ Market data integration (Yahoo) + TTL cache + watchlist + snapshots/candles.
3. ✅ Indicator layer (SMA/EMA/RSI/MACD, hand-computed in pandas) + explicit signal rules.
4. ✅ Top movers ranking from watchlist (daily/weekly windows, sign-based gainers/losers).
5. LLM report layer (grounding -> JSON) with Pydantic validation. **(next)**
6. Chat agent: function calling + `get_stock_data` tool + grounding.
7. Firestore persistence + frontend (dashboard, charts, report, Top movers, chat, disclaimer).
8. Scheduler (GitHub Actions cron) + CI/CD.
