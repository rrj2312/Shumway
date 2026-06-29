# Shumway

[![Live Demo](https://img.shields.io/badge/demo-live-1BD488)](https://shumway-frontend.vercel.app)
[![API Docs](https://img.shields.io/badge/API-docs-055B65)](https://shumway.onrender.com/docs)
[![Python](https://img.shields.io/badge/python-3.x-blue)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-16-black)](https://nextjs.org/)

An early-warning system for corporate financial distress in Indian listed companies, built on Tyler Shumway's (2001) discrete-time hazard model. Shumway predicts the probability that a company enters financial distress in the **following fiscal year**, based on the current year's accounting ratios — using only information that would actually have been available at the time.

**[Live demo →](https://shumway-frontend.vercel.app)** · **[API reference →](https://shumway.onrender.com/docs)**

![Shumway watchlist dashboard](docs/screenshot-watchlist.png)

---

## Table of Contents

- [Description](#description)
- [Built With](#built-with)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [Usage](#usage)
  - [Quick Start](#quick-start)
  - [API Examples](#api-examples)
  - [Configuration](#configuration)
- [Why This Is Harder Than It Looks](#why-this-is-harder-than-it-looks)
- [A Real Methodology Bug, Found and Fixed](#a-real-methodology-bug-found-and-fixed)
- [The Data Journey](#the-data-journey)
- [The Model](#the-model)
- [Architecture](#architecture)
- [Limitations, Stated Plainly](#limitations-stated-plainly)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Description

Shumway tracks 169 NSE/BSE-listed Indian companies and computes a hazard score for each: the modeled probability that the company will enter financial distress within the next fiscal year. Rather than a black-box risk score, it surfaces five interpretable financial signals per company (profitability, leverage, interest coverage, cash flow divergence, return on equity), each shown with a plain-English description and a GREEN/AMBER/RED status.

**Core features:**

- A trained hazard model evaluated out-of-sample at **0.8897 AUC-ROC**, against a simplified Altman Z-score baseline of **0.6412**
- A weekly automated pipeline (ingestion → feature computation → scoring → threshold alerts) via APScheduler — deliberately *not* including automatic retraining (explained below)
- A **live-scoring endpoint** that pulls a company's most recent quarterly filing directly from yfinance and scores it through the same trained model, giving a genuine current-day forecast for any listed company
- A dashboard that surfaces the model's small sample size directly in the UI and API, rather than burying it in documentation

## Built With

| Layer | Tools |
|---|---|
| Historical data | [Kaggle](https://www.kaggle.com/) (annual financials, 4,492 companies) |
| Live data | [yfinance](https://github.com/ranaroussi/yfinance) |
| Storage | SQLite |
| Modeling | pandas, scikit-learn, statsmodels, SHAP |
| Backend | FastAPI, APScheduler |
| Frontend | Next.js, TypeScript, Tailwind CSS, Recharts |
| Deployment | Render (API), Vercel (frontend) |

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+ and npm
- A free [Kaggle](https://www.kaggle.com/) account + API token, if you want to re-run ingestion from scratch (not required to run the app — a populated database ships with the repo)

### Installation

**Backend:**

```bash
git clone https://github.com/rrj2312/Shumway.git
cd Shumway
python -m venv venv
source venv/Scripts/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

The repository ships with a populated `shumway.db` and a trained model (`model/shumway_model.pkl`, `model/scaler.pkl`, `model/winsorize_bounds.pkl`), so you can run the API immediately without re-running ingestion or training.

**Frontend:**

```bash
git clone https://github.com/rrj2312/shumway-frontend.git
cd shumway-frontend
npm install
```

---

## Usage

### Quick Start

**Run the backend:**

```bash
uvicorn main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` for interactive API documentation.

**Run the frontend** (in a separate terminal):

```bash
cd shumway-frontend
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev
```

Visit `http://localhost:3000`.

### API Examples

```bash
# Top companies by forecast hazard probability
curl http://localhost:8000/watchlist

# Full dashboard for one company
curl http://localhost:8000/company/YESBANK_NS

# Live forecast for any currently-listed company, using real-time yfinance data
curl http://localhost:8000/company/live/TCS.NS

# Dataset summary, including the small-sample caveat
curl http://localhost:8000/stats
```

Example response from `/company/live/TCS.NS`:

```json
{
  "ticker": "TCS.NS",
  "as_of_quarter": "2026-03-31",
  "features": {
    "profitability": 0.0752,
    "leverage": 0.4052,
    "interest_coverage": 70.29,
    "cf_divergence": 0.0099,
    "roe": 0.1265
  },
  "hazard_probability": 0.07034,
  "features_available": 5,
  "note": "Live forecast computed from yfinance's most recent quarterly filing..."
}
```

### Configuration

| Variable | Where | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `shumway-frontend/.env.local` | Points the frontend at a running backend (`http://localhost:8000` locally, the Render URL in production) |
| `SHUMWAY_DB` | Backend environment (optional) | Override the SQLite file path; defaults to `shumway.db` in the project root |

To re-run the full data pipeline from scratch (optional — requires a Kaggle API token in `~/.kaggle/kaggle.json`):

```bash
python -m ingestion.kaggle_fetcher
python -m features.compute
python -m features.panel
python -m model.train
python -m model.score
python -m alerts.monitor
```

---

## Why This Is Harder Than It Looks

The central problem with building a distress-prediction model for the Indian market is that well-documented, publicly verified corporate failures are genuinely rare. This model is trained on exactly **6 labeled historical distress events**:

| Company | Event | Basis Fiscal Year |
|---|---|---|
| Suzlon Energy | CARE downgrade to D, debt restructuring | FY2014 |
| Jet Airways | Operations ceased, NCLT insolvency | FY2018 |
| CG Power | Accounting fraud disclosed | FY2018 |
| Yes Bank | RBI moratorium | FY2019 |
| Future Retail | Default, insolvency proceedings | FY2020 |
| Reliance Capital | RBI superseded the board | FY2021 |

*(Basis fiscal year = the year whose ratios were used to predict the following year's actual event — see the methodology fix below.)*

Six positive examples is far below the conventional statistical comfort zone for logistic regression — common rules of thumb want 10–20 events per predictor, and this model has 5 predictors. This is a real, irreducible constraint of the available public data, not a shortcut, and the project is built around acknowledging it:

- Standard maximum-likelihood logistic regression (`statsmodels`) **fails outright** on this data, hitting a singular Hessian from perfect separation. The model uses **L2-regularized logistic regression** (`scikit-learn`, `class_weight='balanced'`) instead — a standard, disclosed adaptation for small-N positive classes, not a deviation from Shumway's underlying functional form.
- The **negative class was deliberately expanded** from an initial curated set of 19 companies to **169 companies**, sampled across the full Kaggle universe of 4,492 Indian listed firms — giving the model a genuinely broad baseline of "what normal looks like" rather than contrasting 6 sick companies against a handful of hand-picked large-caps. This measurably improved discrimination.
- **Retraining is intentionally excluded** from the automated weekly pipeline. Given how dramatically small changes affected results during development, an unsupervised retrain with no validation gate risks silently degrading the model. Retraining stays a manual, reviewed step.

## A Real Methodology Bug, Found and Fixed

This is the single most consequential fix in the project.

**The bug:** the original panel construction paired each fiscal year's financial ratios with *that same fiscal year's* distress label. Yes Bank's FY2020 row (the year of its actual RBI moratorium) was labeled `distress=1`, and the model learned to associate FY2020's ratios with FY2020's outcome.

This means the model was answering the wrong question — *"do this year's ratios look like a company already in crisis"* (concurrent classification) rather than *"do this year's ratios predict the company will enter crisis next year"* (the actual forecasting task an early-warning system needs to perform).

**The fix:** distress labels are shifted back one fiscal year relative to the features, and the original event year is excluded entirely from the training panel:

```python
distress_df["target_quarter"] = (distress_df["quarter"].astype(int) - 1).astype(str)
```

Yes Bank's label moved from FY2020 to FY2019. Jet Airways moved from FY2019 to FY2018. And so on for all 6 events.

**The result:** out-of-sample AUC-ROC improved from **0.701 to 0.8897** on this genuinely harder, more honest task — likely because a company's ratios *one year before* collapse form a more universal signature across different failure mechanisms than the ratios *in* the collapse year, which vary wildly by the specific nature of the failure.

**Honest caveat:** the corrected evaluation split has only **2 distress events in the test set**. This AUC should be read as directionally meaningful, not a precise estimate.

## The Data Journey

This project went through three full data-source pivots, each forced by a discovered limitation:

1. **yfinance** (abandoned for training) — only returns a shallow trailing window (4–8 quarters) of financials, with inconsistent cash flow coverage. No historical depth to reach 2018–2020 distress events. *(Still used today for the live-scoring endpoint, where current data is exactly what's needed.)*
2. **Kaggle, quarterly frequency** (abandoned) — only covered 2020 onward for most companies, capturing Yes Bank's recovery, not its collapse.
3. **Kaggle, annual frequency** (final) — reaches back to FY2006–2013, covering every known distress event's lead-up. This forced an annual-frequency design for the whole project, consistent with a substantial share of published bankruptcy-prediction literature, which faces the same data-availability constraint.

Notable bugs surfaced and fixed along the way:

- **Balance sheet identity bug** — Kaggle's `"Total Liabilities"` line item actually equals *Liabilities + Equity*, not liabilities alone, silently making every company's leverage compute as exactly `1.0`. Fixed by reconstructing leverage from the dataset's actual component line items.
- **Date-format mismatch** — income statement columns used `"Mar 2019"`, balance sheet used `"2019-03-01"`; a parser written for one format silently rejected the other.
- **Winsorize-bounds instability** — outlier-clipping bounds were recomputed fresh at scoring time instead of reusing training-time bounds, causing visibly inconsistent results between training and inference.
- **Stale benchmark ticker** — `^CNX500` (Nifty 500) was delisted on Yahoo Finance, silently returning zero rows for the project's duration without ever throwing a visible error.

## The Model

Mathematically a pooled logistic regression on panel data: each row is one company-year, estimating the probability of `distress = 1` in the following year.

**Features (5):** `profitability`, `leverage`, `interest_coverage`, `cf_divergence`, `roe` — see [API Examples](#api-examples) above for exact formulas in a live response.

**Estimator:** `sklearn.linear_model.LogisticRegression`, `penalty='l2'`, `C=0.05`, `class_weight='balanced'`. Features are standardized and winsorized at the 1st/99th percentile, with both transformations fit once at training time and persisted for consistent inference.

**Evaluation:** time-based train/test split, AUC-ROC and AUC-PR, benchmarked against a simplified Altman Z-score proxy.

## Architecture

```
Kaggle dataset (4,492 cos., annual)
            │
            ▼
SQLite (raw_financials → features → lagged panel)
            │
            ▼
L2-regularized logistic regression (scikit-learn)
            │
   ┌────────┴────────┐
   ▼                 ▼
FastAPI (Render)   yfinance live path
  /watchlist         /company/live/{ticker}
  /company/{id}      (current-day, independent
  /alerts /stats      of the training panel)
   │
   ▼
Next.js (Vercel)
  Watchlist · Company detail · Alerts · Live Lookup
```

## Limitations, Stated Plainly

- **Training data is frozen at FY2023** — Kaggle's dataset is a static snapshot; no actively maintained source currently provides the same historical depth for more recent years.
- **6 distress events is a genuine statistical limitation.** Reported AUC figures should be read directionally, not as precise, production-grade estimates.
- **The model cannot anticipate fraud- or governance-driven distress** as reliably as ratio-driven deterioration — CG Power's fraud-driven collapse scored only 0.479 (ELEVATED, not HIGH).
- **`current_ratio` and `gross_margin`** from the original 12-signal specification are not computable from the Kaggle source and are excluded rather than approximated.
- **Live yfinance scoring has inconsistent cash flow coverage** across companies; affected requests degrade gracefully to 4-of-5 features, with `features_available` explicitly returned.

## Roadmap

- [ ] Expand the positive class with additional verified Indian distress cases (Religare, Vakrangee, Reliance Home Finance, Alok Industries)
- [ ] Add a validation gate for automated retraining (only replace the saved model if AUC and event count don't regress)
- [ ] Source quarterly data for the historical distress window specifically, to support quarterly-resolution forecasting

## Contributing

This is currently a personal portfolio project and isn't accepting external contributions, but feedback and issue reports are welcome via GitHub Issues.

## License

MIT
