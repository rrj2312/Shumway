import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from database.db import get_connection
from ingestion.watchlist import WATCHLIST, NIFTY500_TICKER
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


def quarter_label(dt) -> str:
    """Convert a datetime to 'YYYY-QN' string. E.g. 2023-04-01 → '2023-Q1'"""
    q = (dt.month - 1) // 3 + 1
    return f"{dt.year}-Q{q}"


def fetch_quarterly_financials(ticker_symbol: str, company_id: str) -> int:
    """
    Pull income statement, balance sheet, cash flow from yfinance.
    Stores each line item as a row in raw_financials.
    Returns number of rows upserted.
    """
    ticker = yf.Ticker(ticker_symbol)
    rows_written = 0

    statement_map = {
        "income":   ticker.quarterly_income_stmt,
        "balance":  ticker.quarterly_balance_sheet,
        "cashflow": ticker.quarterly_cashflow,
    }

    with get_connection() as conn:
        for stmt_type, df in statement_map.items():
            if df is None or df.empty:
                log.warning(f"[{company_id}] No {stmt_type} data from yfinance")
                continue

            # yfinance returns dates as columns, line items as index
            for col in df.columns:
                quarter = quarter_label(col)
                for line_item, value in df[col].items():
                    if pd.isna(value):
                        continue
                    conn.execute("""
                        INSERT INTO raw_financials
                            (company_id, quarter, stmt_type, line_item, value)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(company_id, quarter, stmt_type, line_item)
                        DO UPDATE SET value=excluded.value, fetched_at=CURRENT_TIMESTAMP
                    """, (company_id, quarter, stmt_type, str(line_item), float(value)))
                    rows_written += 1

    log.info(f"[{company_id}] Financials: {rows_written} rows upserted")
    return rows_written


def fetch_price_history(ticker_symbol: str, company_id: str, period: str = "5y") -> int:
    """
    Pull daily OHLCV from yfinance.
    Computes approximate market cap from Close × shares outstanding.
    Returns number of rows upserted.
    """
    ticker = yf.Ticker(ticker_symbol)
    hist = ticker.history(period=period)

    if hist.empty:
        log.warning(f"[{company_id}] No price history returned")
        return 0

    # shares_outstanding may not always be available; fall back to None
    info = ticker.fast_info
    shares = getattr(info, "shares", None)

    rows_written = 0
    with get_connection() as conn:
        for date, row in hist.iterrows():
            market_cap = (row["Close"] * shares) if shares else None
            conn.execute("""
                INSERT INTO price_history
                    (company_id, date, close, volume, market_cap)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(company_id, date)
                DO UPDATE SET
                    close=excluded.close,
                    volume=excluded.volume,
                    market_cap=excluded.market_cap,
                    fetched_at=CURRENT_TIMESTAMP
            """, (
                company_id,
                date.strftime("%Y-%m-%d"),
                float(row["Close"]),
                int(row["Volume"]) if row["Volume"] else None,
                float(market_cap) if market_cap else None,
            ))
            rows_written += 1

    log.info(f"[{company_id}] Price history: {rows_written} rows upserted")
    return rows_written


def fetch_nifty500(period: str = "5y") -> int:
    """Fetch Nifty 500 index daily closes for benchmark computations."""
    ticker = yf.Ticker(NIFTY500_TICKER)
    hist = ticker.history(period=period)

    if hist.empty:
        log.warning("Nifty 500 data empty — check ticker symbol")
        return 0

    rows_written = 0
    with get_connection() as conn:
        for date, row in hist.iterrows():
            conn.execute("""
                INSERT INTO nifty500_history (date, close)
                VALUES (?, ?)
                ON CONFLICT(date)
                DO UPDATE SET close=excluded.close, fetched_at=CURRENT_TIMESTAMP
            """, (date.strftime("%Y-%m-%d"), float(row["Close"])))
            rows_written += 1

    log.info(f"Nifty 500: {rows_written} rows upserted")
    return rows_written


def run_full_ingestion():
    """Ingest all companies in the watchlist. Called by APScheduler or manually."""
    log.info("=== Starting full ingestion run ===")
    fetch_nifty500()

    for ticker_symbol, display_name, sector, is_bank in WATCHLIST:
        company_id = ticker_symbol.replace(".", "_")   # YESBANK_NS
        log.info(f"--- Ingesting {display_name} ({ticker_symbol}) ---")
        try:
            fetch_quarterly_financials(ticker_symbol, company_id)
            fetch_price_history(ticker_symbol, company_id)
        except Exception as e:
            log.error(f"[{company_id}] Ingestion failed: {e}", exc_info=True)

    log.info("=== Ingestion run complete ===")


if __name__ == "__main__":
    from database.db import init_db
    init_db()
    run_full_ingestion()