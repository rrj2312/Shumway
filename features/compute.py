import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

from database.db import get_connection
from features.accounting import compute_accounting_features
from features.market import compute_market_features

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


def get_all_ingested_company_ids() -> list[str]:
    """
    Returns every distinct company_id present in raw_financials,
    regardless of whether it came from the curated WATCHLIST or
    the bulk Kaggle sample. This avoids needing to maintain two
    separate company lists in sync.
    """
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT DISTINCT company_id FROM raw_financials
            WHERE stmt_type = 'income'
        """).fetchall()
    return [r["company_id"] for r in rows]


def run_full_feature_computation():
    """Recompute features for every company that has ingested data."""
    log.info("=== Starting feature computation ===")
    total, success = 0, 0
    company_ids = get_all_ingested_company_ids()
    log.info(f"Found {len(company_ids)} companies with ingested data")

    for company_id in company_ids:
        quarters = get_available_quarters(company_id)
        for quarter in quarters:
            total += 1
            if compute_and_store_features(company_id, quarter):
                success += 1

    log.info(f"=== Feature computation complete: {success}/{total} succeeded ===")


if __name__ == "__main__":
    run_full_feature_computation()