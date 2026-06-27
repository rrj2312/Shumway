import yfinance as yf
import pandas as pd
import numpy as np
import logging
from model.train import load_model, FEATURE_COLS, WINSORIZE_BOUNDS_PATH
import pickle

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


def pick(*keys, source: dict):
    """Try multiple yfinance line-item spellings, return first non-None hit."""
    for k in keys:
        v = source.get(k)
        if v is not None and not pd.isna(v):
            return float(v)
    return None


def fetch_live_features(ticker_symbol: str) -> dict:
   
    ticker = yf.Ticker(ticker_symbol)

    income = ticker.quarterly_income_stmt
    balance = ticker.quarterly_balance_sheet
    cashflow = ticker.quarterly_cashflow

    if income is None or income.empty:
        raise ValueError(f"No income statement data for {ticker_symbol}")
    if balance is None or balance.empty:
        raise ValueError(f"No balance sheet data for {ticker_symbol}")

    # Use the most recent quarter (first column)
    latest_income_col = income.columns[0]
    latest_balance_col = balance.columns[0]

    inc = {str(k).lower().replace(" ", "_"): v for k, v in income[latest_income_col].items()}
    bal = {str(k).lower().replace(" ", "_"): v for k, v in balance[latest_balance_col].items()}

    cf = {}
    if cashflow is not None and not cashflow.empty:
        latest_cf_col = cashflow.columns[0]
        cf = {str(k).lower().replace(" ", "_"): v for k, v in cashflow[latest_cf_col].items()}

    # --- Extract raw values, yfinance naming conventions ---
    ebit = pick("ebit", "operating_income", source=inc)
    interest_exp = pick("interest_expense", "interest_expense_non_operating", source=inc)
    net_income = pick("net_income", "net_income_common_stockholders", source=inc)
    profit_before_tax = pick("pretax_income", "pretax_income_loss", source=inc)

    total_assets = pick("total_assets", source=bal)
    total_liabilities = pick(
        "total_liabilities_net_minority_interest", "total_liab", source=bal
    )
    total_equity = pick(
        "total_equity_gross_minority_interest", "stockholders_equity",
        "common_stock_equity", source=bal
    )
    op_cashflow = pick(
        "operating_cash_flow", "cash_flow_from_continuing_operating_activities",
        source=cf
    )

    # --- Compute the 5 model features ---
    def safe_div(n, d):
        if n is None or d is None or d == 0:
            return None
        return n / d

    profitability = safe_div(net_income, total_assets)
    leverage = safe_div(total_liabilities, total_assets)

    cf_divergence = None
    if net_income is not None and op_cashflow is not None and total_assets:
        cf_divergence = (net_income - op_cashflow) / total_assets

    ebit_proxy = None
    if profit_before_tax is not None and interest_exp is not None:
        ebit_proxy = profit_before_tax + interest_exp
    elif ebit is not None:
        ebit_proxy = ebit
    interest_coverage = safe_div(ebit_proxy, interest_exp)

    roe = safe_div(net_income, total_equity)

    features = {
        "profitability": profitability,
        "leverage": leverage,
        "interest_coverage": interest_coverage,
        "cf_divergence": cf_divergence,
        "roe": roe,
    }

    missing = [k for k, v in features.items() if v is None]
    if missing:
        log.warning(f"[{ticker_symbol}] Missing features: {missing}")

    return {
        "features": features,
        "as_of_quarter": str(latest_income_col)[:10],
    }


def score_live_company(ticker_symbol: str) -> dict:
    """
    Full pipeline: fetch live yfinance data -> compute features ->
    apply training-time winsorize bounds -> scale -> predict.
    """
    model, scaler = load_model()

    with open(WINSORIZE_BOUNDS_PATH, "rb") as f:
        bounds = pickle.load(f)

    live_data = fetch_live_features(ticker_symbol)
    raw_features = live_data["features"]

    n_available = sum(1 for v in raw_features.values() if v is not None)
    if n_available < 3:
        raise ValueError(
            f"Only {n_available}/5 features available for {ticker_symbol} -- "
            f"too sparse for a reliable score"
        )

    # Fill missing with the training-time median (approximated as the
    # winsorize bound midpoint, since we don't store the median separately --
    # this is a reasonable fallback for the rare missing feature)
    row = []
    for col in FEATURE_COLS:
        value = raw_features.get(col)
        if value is None:
            lower, upper = bounds[col]
            value = (lower + upper) / 2
        else:
            lower, upper = bounds[col]
            value = max(lower, min(upper, value))  # apply same winsorize clip
        row.append(value)

    X = np.array(row).reshape(1, -1)
    X_scaled = scaler.transform(X)
    probability = float(model.predict_proba(X_scaled)[0, 1])

    return {
        "ticker": ticker_symbol,
        "as_of_quarter": live_data["as_of_quarter"],
        "features": raw_features,
        "hazard_probability": round(probability, 5),
        "features_available": n_available,
        "note": (
            "Live forecast computed from yfinance's most recent quarterly filing. "
            "This is a current snapshot, not historically validated like the "
            "Kaggle-trained backtest -- treat as directional."
        ),
    }


if __name__ == "__main__":
    import sys
    ticker = sys.argv[1] if len(sys.argv) > 1 else "TCS.NS"
    result = score_live_company(ticker)
    for k, v in result.items():
        print(f"{k}: {v}")