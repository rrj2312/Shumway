
import pandas as pd
import numpy as np
import shap
import logging
from database.db import get_connection
from model.train import (
    load_model, FEATURE_COLS, prepare_training_data
)
from features.panel import build_panel

log = logging.getLogger(__name__)


def classify_risk_tier(prob: float, red_signal_count: int) -> str:
    if prob >= 0.60 or red_signal_count >= 7:
        return "HIGH"
    elif prob >= 0.30 or red_signal_count >= 4:
        return "ELEVATED"
    return "LOW"


def count_red_signals(features: dict) -> int:
    red = 0
    checks = [
        (features.get("interest_coverage"), lambda v: v < 1.0),
        (features.get("leverage"),           lambda v: v > 0.85),
        (features.get("current_ratio"),       lambda v: v < 1.0),
        (features.get("cf_divergence"),       lambda v: v < -0.05),
        (features.get("roe"),                 lambda v: v < -0.05),
        (features.get("gross_margin"),        lambda v: v < 0.05),
        (features.get("return_volatility"),   lambda v: v > 0.04),
    ]
    for value, condition in checks:
        if value is not None:
            try:
                if condition(value):
                    red += 1
            except Exception:
                pass
    return red


def score_all_companies():
   
    model, scaler = load_model()
    panel = build_panel()

    if panel.empty:
        log.error("Empty panel — nothing to score")
        return

    # Get latest quarter per company
    latest = panel.sort_values("quarter").groupby("company_id").last().reset_index()

    # Prepare features
    X, y, company_ids, quarters, df_clean = prepare_training_data(latest)

    if X.empty:
        log.error("No scoreable rows after feature prep")
        return

    X_scaled = scaler.transform(X)
    X_scaled_df = pd.DataFrame(X_scaled, columns=FEATURE_COLS, index=X.index)

    # SHAP values for interpretability
    try:
        explainer = shap.LinearExplainer(model, X_scaled_df, feature_perturbation="correlation_dependent")
        shap_values = explainer.shap_values(X_scaled_df)
        shap_df = pd.DataFrame(shap_values, columns=FEATURE_COLS, index=X.index)
    except Exception as e:
        log.warning(f"SHAP computation failed: {e}")
        shap_df = None

    # Predict
    probabilities = model.predict(X_scaled_df)

    with get_connection() as conn:
        for idx, (row_idx, features_row) in enumerate(X_scaled_df.iterrows()):
            company_id = company_ids.iloc[idx]
            quarter    = quarters.iloc[idx]
            prob       = float(probabilities.iloc[idx])

            # Get unscaled features for signal counting
            raw_features = {col: X.iloc[idx][col] for col in FEATURE_COLS}
            red_count = count_red_signals(raw_features)
            tier = classify_risk_tier(prob, red_count)

            # Previous quarter score delta
            prev = conn.execute("""
                SELECT hazard_probability FROM scores
                WHERE company_id=? AND quarter < ?
                ORDER BY quarter DESC LIMIT 1
            """, (company_id, quarter)).fetchone()
            score_delta = (prob - prev["hazard_probability"]) if prev else None

            conn.execute("""
                INSERT INTO scores
                    (company_id, quarter, hazard_probability, risk_tier,
                     score_delta, red_signal_count)
                VALUES (?,?,?,?,?,?)
                ON CONFLICT(company_id, quarter) DO UPDATE SET
                    hazard_probability=excluded.hazard_probability,
                    risk_tier=excluded.risk_tier,
                    score_delta=excluded.score_delta,
                    red_signal_count=excluded.red_signal_count,
                    scored_at=CURRENT_TIMESTAMP
            """, (company_id, quarter, prob, tier, score_delta, red_count))

            log.info(f"[{company_id}/{quarter}] prob={prob:.3f} tier={tier} red={red_count}")


if __name__ == "__main__":
    score_all_companies()