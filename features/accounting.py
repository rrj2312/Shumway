import pandas as pd
from database.db import get_connection
import logging

log = logging.getLogger(__name__)


def get_stmt_values(company_id: str, quarter: str, stmt_type: str) -> dict:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT line_item, value FROM raw_financials
            WHERE company_id=? AND quarter=? AND stmt_type=?
        """, (company_id, quarter, stmt_type)).fetchall()

    result = {}
    for row in rows:
        key = row["line_item"].lower().replace(" ", "_").replace("%", "pct").strip("_")
        result[key] = row["value"]
    return result


def safe_div(numerator, denominator, default=None):
    try:
        if denominator is None or denominator == 0:
            return default
        return numerator / denominator
    except (TypeError, ZeroDivisionError):
        return default


def compute_accounting_features(company_id: str, quarter: str) -> dict:
    inc = get_stmt_values(company_id, quarter, "income")
    bal = get_stmt_values(company_id, quarter, "balance")
    cf  = get_stmt_values(company_id, quarter, "cashflow")

    revenue           = inc.get("revenue")
    interest_exp      = inc.get("interest")
    net_income        = inc.get("net_profit")
    profit_before_tax = inc.get("profit_before_tax")

    # Kaggle's "Total Liabilities" = Liabilities + Equity (balance sheet identity),
    # NOT liabilities alone. Use the real components instead.
    borrowings         = bal.get("borrowings")
    other_liabilities  = bal.get("other_liabilities")
    equity_capital     = bal.get("equity_capital")
    reserves           = bal.get("reserves")
    total_assets       = bal.get("total_assets")   # = total liabilities + equity, used as a size denominator only

    # Real liabilities = borrowings + other liabilities (excludes equity)
    real_liabilities = None
    if borrowings is not None or other_liabilities is not None:
        real_liabilities = (borrowings or 0) + (other_liabilities or 0)

    # Real equity = equity capital + reserves
    total_equity = None
    if equity_capital is not None or reserves is not None:
        total_equity = (equity_capital or 0) + (reserves or 0)

    op_cashflow = cf.get("cash_from_operating_activity")

    # --- Shumway model variables ---
    profitability = safe_div(net_income, total_assets)

    # Leverage: real liabilities (debt) / total assets — NOT liabilities/liabilities
    leverage = safe_div(real_liabilities, total_assets)

    cf_divergence = None
    if net_income is not None and op_cashflow is not None and total_assets:
        cf_divergence = (net_income - op_cashflow) / total_assets

    # --- Dashboard signals ---
    ebit_proxy = None
    if profit_before_tax is not None and interest_exp is not None:
        ebit_proxy = profit_before_tax + interest_exp
    interest_coverage = safe_div(ebit_proxy, interest_exp)

    # Debt/Equity: now uses real liabilities and real equity
    debt_equity = safe_div(real_liabilities, total_equity)
    roe         = safe_div(net_income, total_equity)

    current_ratio = None  # not computable from Kaggle schema
    gross_margin  = None  # not computable from Kaggle schema

    return {
        "profitability":     profitability,
        "leverage":          leverage,
        "cf_divergence":     cf_divergence,
        "interest_coverage": interest_coverage,
        "debt_equity":       debt_equity,
        "current_ratio":     current_ratio,
        "roe":               roe,
        "gross_margin":      gross_margin,
    }