import logging
from database.db import get_connection
from features.accounting import compute_accounting_features
from features.market import compute_market_features
from ingestion.watchlist import WATCHLIST

log = logging.getLogger(__name__)


def get_available_quarters(company_id: str) -> list[str]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT DISTINCT quarter FROM raw_financials
            WHERE company_id=? AND stmt_type='income'
            ORDER BY quarter
        """, (company_id,)).fetchall()
    return [r["quarter"] for r in rows]


def compute_and_store_features(company_id: str, quarter: str) -> bool:
   
    try:
        acc = compute_accounting_features(company_id, quarter)
        mkt = compute_market_features(company_id, quarter)

        row = {**acc, **mkt}

        row = {k: v for k, v in row.items() if not k.startswith("_")}

        with get_connection() as conn:
            conn.execute("""
                INSERT INTO features (
                    company_id, quarter,
                    interest_coverage, leverage, profitability, cf_divergence,
                    current_ratio, roe, gross_margin,
                    rel_size, excess_return, return_volatility
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(company_id, quarter) DO UPDATE SET
                    interest_coverage=excluded.interest_coverage,
                    leverage=excluded.leverage,
                    profitability=excluded.profitability,
                    cf_divergence=excluded.cf_divergence,
                    current_ratio=excluded.current_ratio,
                    roe=excluded.roe,
                    gross_margin=excluded.gross_margin,
                    rel_size=excluded.rel_size,
                    excess_return=excluded.excess_return,
                    return_volatility=excluded.return_volatility,
                    computed_at=CURRENT_TIMESTAMP
            """, (
                company_id, quarter,
                row.get("interest_coverage"),
                row.get("leverage"),
                row.get("profitability"),
                row.get("cf_divergence"),
                row.get("current_ratio"),
                row.get("roe"),
                row.get("gross_margin"),
                row.get("rel_size"),
                row.get("excess_return"),
                row.get("return_volatility"),
            ))
        return True
    except Exception as e:
        log.error(f"[{company_id}/{quarter}] Feature computation failed: {e}", exc_info=True)
        return False


def run_full_feature_computation():
    log.info("=== Starting feature computation ===")
    total, success = 0, 0
    for ticker_symbol, *_ in WATCHLIST:
        company_id = ticker_symbol.replace(".", "_")
        quarters = get_available_quarters(company_id)
        log.info(f"[{company_id}] Computing features for {len(quarters)} quarters")
        for quarter in quarters:
            total += 1
            if compute_and_store_features(company_id, quarter):
                success += 1
    log.info(f"=== Feature computation complete: {success}/{total} succeeded ===")


if __name__ == "__main__":
    run_full_feature_computation()