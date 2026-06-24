import os
import random
import logging
import pandas as pd
from ingestion.kaggle_fetcher import (
    get_dataset_root, ingest_statement_file, KAGGLE_NAME_MAP
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


def make_company_id(kaggle_name: str) -> str:
    
    cleaned = (
        kaggle_name.upper()
        .replace(" LTD", "")
        .replace(".", "")
        .replace(",", "")
        .replace("-", "_")
        .replace("&", "AND")
        .replace("_", " ")
        .strip()
    )
    return "_".join(cleaned.split())


def sample_companies(n: int = 150, seed: int = 42, exclude_existing: bool = True) -> list[str]:
   
    root = get_dataset_root()
    all_companies = os.listdir(root)

    if exclude_existing:
        already_have = set(KAGGLE_NAME_MAP.values())
        all_companies = [c for c in all_companies if c not in already_have]

    random.seed(seed)
    sample = random.sample(all_companies, min(n, len(all_companies)))
    return sample


def run_bulk_ingestion(n: int = 150, seed: int = 42):
    log.info(f"=== Starting bulk ingestion of {n} companies ===")
    dataset_root = get_dataset_root()
    sample = sample_companies(n=n, seed=seed)

    succeeded, failed = 0, 0
    id_map = {}   

    for kaggle_name in sample:
        company_id = make_company_id(kaggle_name)
        company_dir = os.path.join(dataset_root, kaggle_name)

        try:
            income_rows   = ingest_statement_file(company_id, company_dir, "Yearly_Profit_Loss.csv", "income")
            balance_rows  = ingest_statement_file(company_id, company_dir, "Yearly_Balance_Sheet.csv", "balance")
            cashflow_rows = ingest_statement_file(company_id, company_dir, "Yearly_Cash_flow.csv", "cashflow")

            if income_rows > 0 and balance_rows > 0:
                succeeded += 1
                id_map[company_id] = kaggle_name
            else:
                failed += 1
                log.warning(f"[{company_id}] Insufficient data (income={income_rows}, balance={balance_rows}) — skipped")
        except Exception as e:
            failed += 1
            log.error(f"[{company_id}] Ingestion failed: {e}")

    log.info(f"=== Bulk ingestion complete: {succeeded} succeeded, {failed} failed/skipped ===")

    pd.DataFrame(list(id_map.items()), columns=["company_id", "kaggle_name"]).to_csv(
        "data/bulk_companies.csv", index=False
    )
    log.info(f"Company ID mapping saved to data/bulk_companies.csv")

    return id_map


if __name__ == "__main__":
    run_bulk_ingestion(n=150)