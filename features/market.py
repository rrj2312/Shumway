import pandas as pd
import numpy as np
from database.db import get_connection
import logging

log = logging.getLogger(__name__)


def get_quarter_date_range(quarter: str):
    
    year, q = quarter.split("-Q")
    year = int(year)
    q = int(q)
    month_start = (q - 1) * 3 + 1
    month_end = q * 3
    start = f"{year}-{month_start:02d}-01"
    if month_end == 12:
        end = f"{year}-12-31"
    else:
        end = f"{year}-{month_end:02d}-{[0,31,28,31,30,31,30][month_end]}"
    return start, end


def fetch_prices(company_id: str, start: str, end: str) -> pd.Series:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT date, close FROM price_history
            WHERE company_id=? AND date BETWEEN ? AND ?
            ORDER BY date
        """, (company_id, start, end)).fetchall()
    if not rows:
        return pd.Series(dtype=float)
    return pd.Series(
        {row["date"]: row["close"] for row in rows}
    )


def fetch_nifty500(start: str, end: str) -> pd.Series:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT date, close FROM nifty500_history
            WHERE date BETWEEN ? AND ?
            ORDER BY date
        """, (start, end)).fetchall()
    if not rows:
        return pd.Series(dtype=float)
    return pd.Series({row["date"]: row["close"] for row in rows})


def fetch_total_market_cap_nifty500(date: str) -> float | None:
   
    with get_connection() as conn:
        row = conn.execute("""
            SELECT SUM(market_cap) AS total
            FROM price_history
            WHERE date = ? AND market_cap IS NOT NULL
        """, (date,)).fetchone()
    return row["total"] if row and row["total"] else None


def compute_market_features(company_id: str, quarter: str) -> dict:
    
    start, end = get_quarter_date_range(quarter)

    prices = fetch_prices(company_id, start, end)
    nifty  = fetch_nifty500(start, end)

    if len(prices) < 10:
        return {"rel_size": None, "excess_return": None, "return_volatility": None}

    # Quarter return
    price_return = (prices.iloc[-1] / prices.iloc[0]) - 1

    # Nifty 500 quarter return
    nifty_return = None
    if len(nifty) >= 10:
        nifty_return = (nifty.iloc[-1] / nifty.iloc[0]) - 1

    excess_return = (price_return - nifty_return) if nifty_return is not None else None

    # Daily return volatility
    daily_returns = prices.pct_change().dropna()
    return_volatility = float(daily_returns.std()) if len(daily_returns) > 5 else None

    rel_size = None
    with get_connection() as conn:
        row = conn.execute("""
            SELECT market_cap FROM price_history
            WHERE company_id=? AND date<=? AND market_cap IS NOT NULL
            ORDER BY date DESC LIMIT 1
        """, (company_id, end)).fetchone()

    if row and row["market_cap"]:
        company_mc = row["market_cap"]
        total_mc = fetch_total_market_cap_nifty500(end)
        if total_mc and total_mc > 0:
            rel_size = float(np.log(company_mc / total_mc))

    return {
        "rel_size":          rel_size,
        "excess_return":     float(excess_return) if excess_return is not None else None,
        "return_volatility": return_volatility,
    }