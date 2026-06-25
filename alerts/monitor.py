from database.db import get_connection
import logging

log = logging.getLogger(__name__)

THRESHOLDS = {
    "high_hazard_prob":    ("hazard_probability", ">",  0.60, "critical"),
    "rising_hazard":       ("score_delta",         ">",  0.15, "warning"),
    "low_interest_cover":  ("interest_coverage",  "<",  1.0,  "critical"),
    "high_leverage":       ("leverage",            ">",  0.85, "warning"),
    "negative_cf_div":     ("cf_divergence",       "<", -0.05, "warning"),
}


def run_alert_scan():
    with get_connection() as conn:
        latest_scores = conn.execute("""
            SELECT s.company_id, s.quarter, s.hazard_probability,
                   s.score_delta, s.risk_tier,
                   f.interest_coverage, f.leverage, f.cf_divergence
            FROM scores s
            JOIN features f ON s.company_id=f.company_id AND s.quarter=f.quarter
            WHERE s.scored_at = (
                SELECT MAX(scored_at) FROM scores s2
                WHERE s2.company_id=s.company_id
            )
        """).fetchall()

        alerts_written = 0
        for row in latest_scores:
            row = dict(row)
            company_id = row["company_id"]
            quarter    = row["quarter"]

            for signal_name, (col, op, threshold, severity) in THRESHOLDS.items():
                value = row.get(col)
                if value is None:
                    continue

                triggered = (
                    (op == ">" and value > threshold) or
                    (op == "<" and value < threshold)
                )
                if not triggered:
                    continue

             
                existing = conn.execute("""
                    SELECT id FROM alerts
                    WHERE company_id=? AND signal=?
                    AND message LIKE ?
                """, (company_id, signal_name, f"%{quarter}%")).fetchone()

                if existing:
                    continue

                message = (
                    f"{company_id} | FY{quarter} | {col} = {value:.3f} "
                    f"(threshold {op} {threshold})"
                )
                conn.execute("""
                    INSERT INTO alerts (company_id, signal, severity, message)
                    VALUES (?, ?, ?, ?)
                """, (company_id, signal_name, severity, message))
                alerts_written += 1
                log.info(f"ALERT [{severity.upper()}]: {message}")

    log.info(f"Alert scan complete: {alerts_written} new alerts written")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run_alert_scan()