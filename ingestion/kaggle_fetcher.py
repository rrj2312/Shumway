import kagglehub
import os
import pandas as pd
import logging
from database.db import get_connection
from ingestion.watchlist import WATCHLIST

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

DATASET_SLUG = "sameerprogrammer/detailed-financial-data-of-4456-nse-and-bse-company"


KAGGLE_NAME_MAP = {
    "YESBANK_NS":    "Yes Bank Ltd",
    "HDFCBANK_NS":   "HDFC Bank Ltd",
    "AXISBANK_NS":   "Axis Bank Ltd",
    "ICICIBANK_NS":  "ICICI Bank Ltd",
    "SBIN_NS":       "State Bank of India",
    "IDFCFIRSTB_NS": "IDFC First Bank Ltd",
    "RELINFRA_NS":   "Reliance Infrastructure Ltd",
    "SUZLON_NS":     "Suzlon Energy Ltd",
    "TATAPOWER_NS":  "Tata Power Company Ltd",   
    "ZEEL_NS":       "Zee Entertainment Enterprises Ltd",
    "INFY_NS":       "Infosys Ltd",
    "TCS_NS":        "Tata Consultancy Services Ltd",
    "NESTLEIND_NS":  "Nestle India Ltd",
    "HINDUNILVR_NS": "Hindustan Unilever Ltd",
    "JETAIRWAYS_NS": "Jet Airways (India) Ltd",
    "CGPOWER_NS":    "CG Power _ Industrial Solutions Ltd",
    "FRETAIL_NS":    "Future Retail Ltd",
    # Distress-case companies not in the live watchlist but needed for labels:
    "RELCAPITAL_NS": "Reliance Capital Ltd",
}


def get_dataset_root() -> str:
    base = kagglehub.dataset_download(DATASET_SLUG)
    nested = os.path.join(
        base,
        "Detailed-Financials-Data-Of-4456-NSE-And-BSE-Company-20231230T233228Z-001",
        "Detailed-Financials-Data-Of-4456-NSE-_-BSE-Company",
    )
    return nested


def parse_year_label(date_str: str) -> str | None:

    date_str = str(date_str).strip()

    if "-" in date_str:
        year_part = date_str.split("-")[0]
        if year_part.isdigit() and len(year_part) == 4:
            return year_part
        return None

    parts = date_str.split()
    if len(parts) == 2 and parts[1].isdigit() and len(parts[1]) == 4:
        return parts[1]

    return None 

def ingest_statement_file(company_id: str, company_dir: str, filename: str, stmt_type: str) -> int:
   
    fpath = os.path.join(company_dir, filename)
    if not os.path.exists(fpath):
        log.warning(f"[{company_id}] {filename} not found")
        return 0

    df = pd.read_csv(fpath)
    if df.empty or df.shape[1] < 2:
        log.warning(f"[{company_id}] {filename} is empty or malformed")
        return 0

    line_item_col = df.columns[0]
    rows_written = 0

    with get_connection() as conn:
        for _, row in df.iterrows():
            line_item = str(row[line_item_col]).strip()
            if not line_item or line_item.lower() == "nan":
                continue

            for col in df.columns[1:]:
                year = parse_year_label(col)
                if year is None:
                    continue   

                value = row[col]
                if pd.isna(value):
                    continue

                try:
                    value = float(value)
                except (ValueError, TypeError):
                    continue   
                conn.execute("""
                    INSERT INTO raw_financials
                        (company_id, quarter, stmt_type, line_item, value)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(company_id, quarter, stmt_type, line_item)
                    DO UPDATE SET value=excluded.value, fetched_at=CURRENT_TIMESTAMP
                """, (company_id, year, stmt_type, line_item, value))
                rows_written += 1

    return rows_written


def ingest_company(company_id: str, kaggle_name: str, dataset_root: str) -> dict:
    company_dir = os.path.join(dataset_root, kaggle_name)

    if not os.path.isdir(company_dir):
        log.error(f"[{company_id}] Kaggle folder not found: '{kaggle_name}'")
        return {"company_id": company_id, "found": False}

    summary = {"company_id": company_id, "found": True}
    summary["income_rows"]   = ingest_statement_file(company_id, company_dir, "Yearly_Profit_Loss.csv", "income")
    summary["balance_rows"]  = ingest_statement_file(company_id, company_dir, "Yearly_Balance_Sheet.csv", "balance")
    summary["cashflow_rows"] = ingest_statement_file(company_id, company_dir, "Yearly_Cash_flow.csv", "cashflow")

    log.info(
        f"[{company_id}] income={summary['income_rows']} "
        f"balance={summary['balance_rows']} cashflow={summary['cashflow_rows']}"
    )
    return summary


def run_kaggle_ingestion():
    log.info("=== Starting Kaggle annual ingestion ===")
    dataset_root = get_dataset_root()
    log.info(f"Dataset root: {dataset_root}")

    results = []
    for company_id, kaggle_name in KAGGLE_NAME_MAP.items():
        result = ingest_company(company_id, kaggle_name, dataset_root)
        results.append(result)

    not_found = [r["company_id"] for r in results if not r["found"]]
    if not_found:
        log.warning(f"Companies NOT found in Kaggle dataset: {not_found}")

    log.info("=== Kaggle ingestion complete ===")
    return results


if __name__ == "__main__":
    from database.db import init_db
    init_db()
    run_kaggle_ingestion()