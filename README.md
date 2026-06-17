# Stock Dashboard (educational)

A web app for **educational** stock-market analysis with a small analytical chat.
Twice a day it computes technical indicators for a watchlist, ranks the top
movers, and generates a news-grounded market-context report. It is **read-only /
analytical** — not a trading bot, and **not investment advice**.

**Live app:** https://stock-dashboard-edu.web.app
**API:** https://stock-dashboard-api-9bcs.onrender.com (`/docs` for the OpenAPI UI)

> Disclaimer shown across the UI: *Educational tool — not investment advice.*

## What it does

- **Daily report** (09:00 & 15:00 Europe/Warsaw): per-ticker indicators + signals,
  Top movers, and an LLM market-context narrative with opportunities, risks and
  cited sources.
- **Watchlist** of US, PL and KR tickers with price, daily/weekly % change, RSI,
  rule-based signals and a price chart (SMA20 / EMA50 overlays).
- **Analytical chat** — name a company; the agent fetches its data and fresh news
  and replies with context and risks (never a buy/sell verdict).

## How it works (key decisions)

- **Numbers are the source of truth, computed in Python.** SMA / EMA / RSI
  (Wilder) / MACD, % changes, signals and the movers ranking are all
  deterministic (pandas). The LLM only narrates — it never invents or overrides
  numbers and never predicts prices.
- **Signals are explicit rules**, e.g. `RSI < 30 AND price > EMA50` =
  "oversold within an uptrend" — not model opinion.
- **LLM = narrative layer.** Gemini receives the already-computed data and adds
  grounded news context. On Gemini 2.5, forced-JSON and Search grounding can't be
  combined, so JSON is requested in the prompt, then **parsed and validated with
  Pydantic**, with a **deterministic fallback** so a report is never empty.
- **Market data: Yahoo Finance chart endpoint** (keyless) for OHLC + price across
  all markets, behind an **async TTL cache** with bounded-concurrency batching.
  (Finnhub's free tier lacks historical candles, so it isn't used.)
- **Top movers come from the watchlist** (sign-based gainers/losers, daily +
  weekly) — reusing cached candles, with no extra API calls.
- **One reusable data/analysis layer** powers the report, the chat tool and the
  movers ranking.

## Tech stack

| Layer        | Choice                                                                 |
| ------------ | ---------------------------------------------------------------------- |
| Frontend     | React + Vite, Tailwind CSS v4, Recharts; Playfair Display + Inter      |
| Backend      | Python + FastAPI, httpx (async), Docker                                |
| Market data  | Yahoo Finance chart endpoint (keyless)                                 |
| Indicators   | pandas (hand-computed SMA/EMA/RSI/MACD) + explicit signal rules        |
| LLM          | Gemini 2.5 Flash (Google AI Studio) + Google Search grounding          |
| Persistence  | Firebase Realtime Database (Admin SDK); in-memory fallback for local   |
| Hosting      | Frontend → Firebase Hosting · Backend → Render (free, Docker)          |
| Scheduler    | GitHub Actions cron → protected `/run-analysis`                        |
| CI           | GitHub Actions (pytest + Vite build, path-filtered)                    |

## Repository layout

```
stock-dashboard-edu/
├── api/                 # FastAPI backend (Docker) — data, indicators, LLM, store
├── web/                 # React + Vite + Tailwind frontend
├── render.yaml          # Render Blueprint for the backend
└── .github/workflows/   # CI (api/web) + scheduled analysis (cron)
```

## API endpoints

| Method | Path                          | Notes                                             |
| ------ | ----------------------------- | ------------------------------------------------- |
| GET    | `/health`                     | Liveness probe                                    |
| GET    | `/watchlist`                  | Configured tickers                                |
| GET    | `/market/{symbol}`            | Snapshot (price + daily % change)                 |
| GET    | `/market/{symbol}/candles`    | Daily OHLCV series                                |
| GET    | `/market/{symbol}/analysis`   | Snapshot + indicators + signals                   |
| GET    | `/top-movers`                 | Daily & weekly gainers/losers                     |
| GET    | `/reports/latest`             | Most recent stored report                         |
| GET    | `/reports/{date}/{session}`   | Report for a date + `morning`/`afternoon`         |
| POST   | `/run-analysis`               | Build + store the report (scheduler only, secret) |
| POST   | `/chat`                       | Analytical chat (context + risks, no verdict)     |

## Local development

```bash
# Backend (http://localhost:8080/docs)
cd api
python -m venv .venv && source .venv/Scripts/activate   # Windows Git Bash
pip install -r requirements-dev.txt
cp .env.example .env                                     # fill in keys
uvicorn app.main:app --reload --port 8080
pytest

# Frontend (http://localhost:5173)
cd web
npm install
npm run dev
```

Secrets live in environment variables (`api/.env` locally, Render env vars /
GitHub Secrets in deployment) and are never committed. See `api/.env.example`.
