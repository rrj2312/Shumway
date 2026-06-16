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

    return {
        row["line_item"].lower().replace(" ", "_"): row["value"]
        for row in rows
    }


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

    def pick(*keys, source):
        for k in keys:
            v = source.get(k)
            if v is not None:
                return v
        return None

    ebit = pick("ebit", "operating_income", "operating_profit", source=inc)
    interest_exp = pick(
        "interest_expense", "finance_cost", "finance_costs",
        "interest_and_finance_charges", source=inc
    )
    net_income = pick(
        "net_income", "profit_after_tax", "net_profit",
        "profit_loss_for_period", source=inc
    )
    total_assets = pick("total_assets", "total_asset", source=bal)
    total_liabilities = pick(
        "total_liabilities", "total_liabilities_net_minority_interest",
        "total_debt", source=bal
    )
    total_equity = pick(
        "total_equity_gross_minority_interest",
        "stockholders_equity", "shareholders_equity",
        "total_stockholder_equity", source=bal
    )
    current_assets = pick("current_assets", "total_current_assets", source=bal)
    current_liabilities = pick(
        "current_liabilities", "total_current_liabilities", source=bal
    )
    revenue = pick("total_revenue", "revenue", "net_sales", "total_income", source=inc)
    gross_profit = pick("gross_profit", source=inc)
    op_cashflow = pick(
        "operating_cash_flow", "cash_flow_from_operations",
        "net_cash_provided_by_operating_activities", source=cf
    )
    total_debt_now = pick(
        "total_debt", "long_term_debt", "long_term_debt_and_capital_lease_obligation",
        source=bal
    )

    #Shumway model variables

    # 1. Profitability: Net Income / Total Assets
    profitability = safe_div(net_income, total_assets)

    # 2. Leverage: Total Liabilities / Total Assets
    leverage = safe_div(total_liabilities, total_assets)

    # 3. CF Divergence: (Net Profit - Operating CF) / Total Assets
    cf_divergence = None
    if net_income is not None and op_cashflow is not None and total_assets:
        cf_divergence = (net_income - op_cashflow) / total_assets

    # dashboard signals

    # Signal 1: Interest Coverage Ratio = EBIT / Interest Expense
    interest_coverage = safe_div(ebit, interest_exp)

    # Signal 2/3: Debt/Equity (absolute) — trend computed at panel level
    debt_equity = safe_div(total_liabilities, total_equity)

    # Signal 4: Current Ratio
    current_ratio = safe_div(current_assets, current_liabilities)

    # Signal 5: CF vs Profit divergence — already computed above as cf_divergence

    # Signal 6: ROE = Net Income / Total Equity
    roe = safe_div(net_income, total_equity)

    # Signal 7: Gross Margin
    gross_margin = safe_div(gross_profit, revenue)

    revenue_val = revenue
    debt_val = total_debt_now

    return {
        "profitability":    profitability,
        "leverage":         leverage,
        "cf_divergence":    cf_divergence,

        "interest_coverage": interest_coverage,
        "debt_equity":       debt_equity,
        "current_ratio":     current_ratio,
        "roe":               roe,
        "gross_margin":      gross_margin,

        "_revenue":          revenue_val,
        "_debt":             debt_val,
        "_total_assets":     total_assets,
        "_net_income":       net_income,
    }