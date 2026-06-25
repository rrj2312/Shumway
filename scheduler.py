from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging

log = logging.getLogger(__name__)
scheduler = BackgroundScheduler()


def run_weekly_pipeline():
    log.info("=== Weekly pipeline starting ===")

    try:
        from ingestion.yfinance_fetcher import run_full_ingestion
        run_full_ingestion()
    except Exception as e:
        log.error(f"Ingestion failed: {e}", exc_info=True)

    try:
        from features.compute import run_full_feature_computation
        run_full_feature_computation()
    except Exception as e:
        log.error(f"Feature computation failed: {e}", exc_info=True)

    try:
        from model.score import score_all_companies
        score_all_companies()
    except Exception as e:
        log.error(f"Scoring failed: {e}", exc_info=True)

    try:
        from alerts.monitor import run_alert_scan
        run_alert_scan()
    except Exception as e:
        log.error(f"Alert scan failed: {e}", exc_info=True)

    log.info("=== Weekly pipeline complete ===")


def start_scheduler():
    scheduler.add_job(
        run_weekly_pipeline,
        trigger=CronTrigger(day_of_week="sun", hour=2, minute=0),
        id="weekly_pipeline",
        replace_existing=True,
    )
    scheduler.start()
    log.info("APScheduler started — weekly pipeline scheduled for Sunday 02:00")


def stop_scheduler():
    scheduler.shutdown()
    log.info("APScheduler stopped")