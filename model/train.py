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
from sklearn.linear_model import LogisticRegression

warnings.filterwarnings("ignore")
log = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).parent / "shumway_model.pkl"
SCALER_PATH = Path(__file__).parent / "scaler.pkl"

FEATURE_COLS = [
    "profitability", "leverage", "interest_coverage", "cf_divergence", "roe",
]


WINSORIZE_BOUNDS_PATH = Path(__file__).parent / "winsorize_bounds.pkl"


def prepare_training_data(panel: pd.DataFrame, fit_bounds: bool = True):

    df = panel.copy()
    df = df.dropna(subset=FEATURE_COLS, thresh=5)

    for col in FEATURE_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        median = df[col].median()
        df[col] = df[col].fillna(median)

    if fit_bounds:
        bounds = {}
        for col in FEATURE_COLS:
            bounds[col] = (df[col].quantile(0.01), df[col].quantile(0.99))
        with open(WINSORIZE_BOUNDS_PATH, "wb") as f:
            pickle.dump(bounds, f)
    else:
        with open(WINSORIZE_BOUNDS_PATH, "rb") as f:
            bounds = pickle.load(f)

    for col in FEATURE_COLS:
        lower, upper = bounds[col]
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
        return None, None, None

    log.info(f"Training on {len(X)} observations, {y.sum()} distress events")

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = LogisticRegression(
        penalty="l2",
        C=0.05,                  
        class_weight="balanced",
        max_iter=1000,
        solver="lbfgs",
    )
    model.fit(X_scaled, y)

    log.info("Fitted L2-regularized logistic regression (sklearn)")
    log.info("Coefficients:")
    for feat, coef in zip(FEATURE_COLS, model.coef_[0]):
        log.info(f"  {feat:<20} {coef:+.4f}")
    log.info(f"  Intercept: {model.intercept_[0]:+.4f}")

    return model, scaler, df_clean


def evaluate_model(model, scaler, panel: pd.DataFrame):
   
    log.info("\n=== Model Evaluation ===")

    X, y, company_ids, quarters, df_clean = prepare_training_data(panel)

    train_mask = quarters.astype(int) < 2020
    test_mask  = quarters.astype(int) >= 2020

    X_train, y_train = X[train_mask], y[train_mask]
    X_test,  y_test  = X[test_mask],  y[test_mask]

    if len(X_test) == 0 or y_test.sum() == 0:
        log.warning("Test set has no distress events — expand date range or watchlist")
        return {}

    if y_train.sum() == 0:
        log.warning("Training set has no distress events — cannot fit evaluation model")
        return {}

    scaler_eval = StandardScaler()
    X_train_scaled = scaler_eval.fit_transform(X_train)
    X_test_scaled  = scaler_eval.transform(X_test)

    eval_model = LogisticRegression(
        penalty="l2",
        C=0.05,
        class_weight="balanced",
        max_iter=1000,
        solver="lbfgs",
    )
    eval_model.fit(X_train_scaled, y_train)

    y_pred = eval_model.predict_proba(X_test_scaled)[:, 1]

    auc_roc = roc_auc_score(y_test, y_pred)
    auc_pr  = average_precision_score(y_test, y_pred)

    log.info(f"Out-of-sample AUC-ROC:         {auc_roc:.4f}")
    log.info(f"Out-of-sample AUC-PR:          {auc_pr:.4f}")
    log.info(f"Test set size:                 {len(X_test)}")
    log.info(f"Distress events in test set:   {y_test.sum()}")
    log.info(f"Distress events in train set:  {y_train.sum()}")

    altman_proxy = (
        1.4 * df_clean.loc[test_mask.values, "roe"].fillna(0)
        + 3.3 * df_clean.loc[test_mask.values, "profitability"].fillna(0)
        - 0.6 * df_clean.loc[test_mask.values, "leverage"].fillna(0)
    )
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
        "distress_events_in_train": int(y_train.sum()),
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