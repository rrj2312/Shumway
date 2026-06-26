import pandas as pd
import numpy as np
from database.db import get_connection
import logging

log = logging.getLogger(__name__)

FEATURE_COLS = [
    "profitability", "leverage", "cf_divergence",
    "interest_coverage", "roe",
    "rel_size", "excess_return", "return_volatility",
]


def build_panel() -> pd.DataFrame:
 
    with get_connection() as conn:
        features_df = pd.read_sql("""
            SELECT company_id, quarter, profitability, leverage, cf_divergence,
                   interest_coverage, roe, rel_size, excess_return, return_volatility
            FROM features
            ORDER BY company_id, quarter
        """, conn)

        distress_df = pd.read_sql("""
            SELECT company_id, quarter, distress
            FROM distress_labels
        """, conn)

    if features_df.empty:
        log.error("No features found — run feature computation first")
        return pd.DataFrame()

    
    distress_df = distress_df.copy()
    distress_df["quarter"] = distress_df["quarter"].astype(int)
    distress_df["target_quarter"] = (distress_df["quarter"] - 1).astype(str)
    distress_df["quarter"] = distress_df["quarter"].astype(str)

    lagged_labels = distress_df[["company_id", "target_quarter", "distress"]].rename(
        columns={"target_quarter": "quarter"}
    )

    panel = features_df.merge(lagged_labels, on=["company_id", "quarter"], how="left")
    panel["distress"] = panel["distress"].fillna(0).astype(int)

    distress_companies = distress_df["company_id"].unique()
    original_event_year = dict(zip(distress_df["company_id"], distress_df["quarter"]))

    rows_to_keep = []
    for company_id, group in panel.groupby("company_id"):
        group = group.sort_values("quarter").reset_index(drop=True)
        if company_id in distress_companies:
            event_year = original_event_year[company_id]
            group = group[group["quarter"].astype(int) < int(event_year)]
        rows_to_keep.append(group)

    panel = pd.concat(rows_to_keep, ignore_index=True)

    log.info(f"Panel built (1-year-ahead prediction): {len(panel)} rows, "
             f"{panel['distress'].sum()} distress events, "
             f"{panel['company_id'].nunique()} companies")

    return panel


def describe_panel(panel: pd.DataFrame):
    print(f"\n{'='*50}")
    print(f"Panel dataset summary")
    print(f"{'='*50}")
    print(f"Total rows:          {len(panel)}")
    print(f"Distress events:     {panel['distress'].sum()}")
    print(f"Companies:           {panel['company_id'].nunique()}")
    print(f"Quarters range:      {panel['quarter'].min()} to {panel['quarter'].max()}")
    print(f"\nClass balance:")
    print(panel['distress'].value_counts(normalize=True).to_string())
    print(f"\nFeature completeness (non-null %):")
    for col in FEATURE_COLS:
        pct = panel[col].notna().mean() * 100
        print(f"  {col:<25} {pct:.1f}%")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    panel = build_panel()
    if not panel.empty:
        describe_panel(panel)
        panel.to_csv("data/panel_dataset.csv", index=False)
        log.info("Panel saved to data/panel_dataset.csv")