import pandas as pd
import numpy as np
import pickle
import warnings
from pathlib import Path
from statsmodels.formula.api import logit
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.preprocessing import StandardScaler
import logging

warnings.filterwarnings("ignore")
log = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).parent / "shumway_model.pkl"
SCALER_PATH = Path(__file__).parent / "scaler.pkl"

FEATURE_COLS = [
    "profitability", "leverage", "cf_divergence",
    "interest_coverage", "current_ratio", "roe", "gross_margin",
    "rel_size", "excess_return", "return_volatility",
]


def prepare_training_data(panel: pd.DataFrame):
   
    # Drop rows with too many missing features
    df = panel.copy()
    df = df.dropna(subset=FEATURE_COLS, thresh=int(len(FEATURE_COLS) * 0.3))

    # Fill remaining NaN with column median
    for col in FEATURE_COLS:
        median = df[col].median()
        df[col] = df[col].fillna(median)

    # Winsorise at 1st/99th percentile
    for col in FEATURE_COLS:
        lower = df[col].quantile(0.01)
        upper = df[col].quantile(0.99)
        df[col] = df[col].clip(lower, upper)

    X = df[FEATURE_COLS]
    y = df["distress"]
    company_ids = df["company_id"]
    quarters = df["quarter"]

    return X, y, company_ids, quarters, df


def train_shumway_model(panel: pd.DataFrame):
   
    X, y, company_ids, quarters, df_clean = prepare_training_data(panel)

    if y.sum() < 3:
        log.error(f"Only {y.sum()} distress events — need more positive examples")
        log.error("Add more companies to watchlist or expand historical window")
        return None, None, None

    log.info(f"Training on {len(X)} observations, {y.sum()} distress events")

    # Standardise
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    X_scaled_df = pd.DataFrame(X_scaled, columns=FEATURE_COLS, index=X.index)

    # Build training DataFrame for statsmodels
    train_df = X_scaled_df.copy()
    train_df["distress"] = y.values
    train_df["company_id"] = company_ids.values

    # Statsmodels formula
    formula = "distress ~ " + " + ".join(FEATURE_COLS)

    model = logit(formula, data=train_df).fit(
        cov_type="cluster",
        cov_kwds={"groups": train_df["company_id"]},
        maxiter=200,
        disp=False,
    )

    log.info("\n" + str(model.summary()))

    return model, scaler, df_clean


def evaluate_model(model, scaler, panel: pd.DataFrame):
   
    log.info("\n=== Model Evaluation ===")

    X, y, company_ids, quarters, df_clean = prepare_training_data(panel)

    train_mask = quarters < "2020-Q1"
    test_mask  = quarters >= "2020-Q1"

    X_train, y_train = X[train_mask], y[train_mask]
    X_test,  y_test  = X[test_mask],  y[test_mask]

    if len(X_test) == 0 or y_test.sum() == 0:
        log.warning("Test set has no distress events — expand date range or watchlist")
        return {}

    scaler_eval = StandardScaler()
    X_train_scaled = scaler_eval.fit_transform(X_train)
    X_test_scaled  = scaler_eval.transform(X_test)

    train_df = pd.DataFrame(X_train_scaled, columns=FEATURE_COLS)
    train_df["distress"] = y_train.values
    train_df["company_id"] = company_ids[train_mask].values

    formula = "distress ~ " + " + ".join(FEATURE_COLS)
    eval_model = logit(formula, data=train_df).fit(
        cov_type="cluster",
        cov_kwds={"groups": train_df["company_id"]},
        maxiter=200,
        disp=False,
    )

    test_df = pd.DataFrame(X_test_scaled, columns=FEATURE_COLS)
    y_pred = eval_model.predict(test_df)

    auc_roc = roc_auc_score(y_test, y_pred)
    auc_pr  = average_precision_score(y_test, y_pred)

    log.info(f"Out-of-sample AUC-ROC:         {auc_roc:.4f}")
    log.info(f"Out-of-sample AUC-PR:          {auc_pr:.4f}")
    log.info(f"Test set size:                 {len(X_test)}")
    log.info(f"Distress events in test set:   {y_test.sum()}")

    # Altman Z-score baseline (simplified, for non-financial companies)
    # Z = 1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 1.0*X5
    # X1 = Working Capital/Assets ≈ (current_ratio-1) proxy
    # X3 = EBIT/Assets ≈ profitability proxy
    # X5 = Revenue/Assets (no revenue in features — skip full Altman)
    # Using simplified version with available features as rough baseline
    altman_proxy = (
        1.2 * df_clean.loc[test_mask.values, "current_ratio"].fillna(0)
        + 1.4 * df_clean.loc[test_mask.values, "roe"].fillna(0)
        + 3.3 * df_clean.loc[test_mask.values, "profitability"].fillna(0)
    )
    # Altman predicts Z<1.8 = distress, so invert: lower Z = higher distress prob
    altman_distress_score = -altman_proxy  

    try:
        altman_auc = roc_auc_score(y_test, altman_distress_score)
        log.info(f"Altman proxy AUC-ROC baseline: {altman_auc:.4f}")
    except Exception:
        altman_auc = None

    metrics = {
        "auc_roc": round(auc_roc, 4),
        "auc_pr":  round(auc_pr, 4),
        "altman_baseline_auc": round(altman_auc, 4) if altman_auc else None,
        "test_size": len(X_test),
        "distress_events_in_test": int(y_test.sum()),
    }
    return metrics


def save_model(model, scaler):
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    with open(SCALER_PATH, "wb") as f:
        pickle.dump(scaler, f)
    log.info(f"Model saved to {MODEL_PATH}")


def load_model():
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
    with open(SCALER_PATH, "rb") as f:
        scaler = pickle.load(f)
    return model, scaler


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from features.panel import build_panel, describe_panel

    panel = build_panel()
    if panel.empty:
        log.error("Empty panel — run ingestion and feature computation first")
        sys.exit(1)

    describe_panel(panel)
    model, scaler, df_clean = train_shumway_model(panel)

    if model is not None:
        metrics = evaluate_model(model, scaler, panel)
        print("\n=== Final Metrics ===")
        for k, v in metrics.items():
            print(f"  {k}: {v}")
        save_model(model, scaler)