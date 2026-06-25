from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from database.db import get_connection, init_db
from scheduler import start_scheduler, stop_scheduler
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
   
    init_db()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="Shumway API",
    description="Indian corporate financial distress early warning system",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   
    allow_methods=["GET"],
    allow_headers=["*"],
)


def normalize_id(identifier: str) -> str:
  
    return identifier.upper().replace(".", "_").replace(" ", "_")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/watchlist")
def get_watchlist(limit: int = Query(default=50, le=500)):
   
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT s.company_id, s.quarter, s.hazard_probability,
                   s.risk_tier, s.score_delta, s.red_signal_count
            FROM scores s
            WHERE s.scored_at = (
                SELECT MAX(scored_at) FROM scores s2
                WHERE s2.company_id = s.company_id
            )
            ORDER BY s.hazard_probability DESC
            LIMIT ?
        """, (limit,)).fetchall()

    return [dict(r) for r in rows]


@app.get("/company/{company_id}")
def get_company_dashboard(company_id: str):
    cid = normalize_id(company_id)

    with get_connection() as conn:
        score = conn.execute("""
            SELECT * FROM scores
            WHERE company_id=?
            ORDER BY quarter DESC LIMIT 1
        """, (cid,)).fetchone()

        if not score:
            raise HTTPException(404, detail=f"No data for {company_id}")

        features = conn.execute("""
            SELECT * FROM features
            WHERE company_id=?
            ORDER BY quarter DESC LIMIT 1
        """, (cid,)).fetchone()

        history = conn.execute("""
            SELECT quarter, hazard_probability, risk_tier, score_delta
            FROM scores WHERE company_id=?
            ORDER BY quarter DESC LIMIT 12
        """, (cid,)).fetchall()

        is_labeled_distress = conn.execute("""
            SELECT distress, event_type, source_note FROM distress_labels
            WHERE company_id=? AND distress=1
            LIMIT 1
        """, (cid,)).fetchone()

    return {
        "company_id": cid,
        "score": dict(score) if score else None,
        "features": dict(features) if features else None,
        "history": [dict(r) for r in history],
        "known_distress_event": dict(is_labeled_distress) if is_labeled_distress else None,
    }


@app.get("/company/{company_id}/signals")
def get_company_signals(company_id: str):
   
    cid = normalize_id(company_id)

    with get_connection() as conn:
        f = conn.execute("""
            SELECT * FROM features WHERE company_id=?
            ORDER BY quarter DESC LIMIT 1
        """, (cid,)).fetchone()

    if not f:
        raise HTTPException(404, detail=f"No features for {company_id}")

    f = dict(f)

    def classify(value, green_range, amber_range):
        if value is None:
            return "UNKNOWN"
        if green_range[0] <= value <= green_range[1]:
            return "GREEN"
        if amber_range[0] <= value <= amber_range[1]:
            return "AMBER"
        return "RED"

    signals = [
        {
            "name": "Interest Coverage Ratio",
            "value": f.get("interest_coverage"),
            "unit": "x",
            "status": classify(f.get("interest_coverage"),
                               green_range=(1.5, 999), amber_range=(1.0, 1.5)),
            "description": "Profit before tax + Interest, divided by Interest. Below 1.0 = critical.",
        },
        {
            "name": "Leverage",
            "value": f.get("leverage"),
            "unit": "",
            "status": classify(f.get("leverage"),
                               green_range=(0, 0.65), amber_range=(0.65, 0.85)),
            "description": "(Borrowings + Other Liabilities) / Total Assets. Above 0.85 = warning.",
        },
        {
            "name": "Profitability",
            "value": f.get("profitability"),
            "unit": "",
            "status": classify(f.get("profitability"),
                               green_range=(0.01, 999), amber_range=(-0.02, 0.01)),
            "description": "Net Profit / Total Assets.",
        },
        {
            "name": "CF Divergence",
            "value": f.get("cf_divergence"),
            "unit": "",
            "status": classify(f.get("cf_divergence"),
                               green_range=(-0.01, 999), amber_range=(-0.05, -0.01)),
            "description": "(Net Profit − Op. Cash Flow) / Assets. Negative = profit without cash.",
        },
        {
            "name": "ROE",
            "value": f.get("roe"),
            "unit": "",
            "status": classify(f.get("roe"),
                               green_range=(0.08, 999), amber_range=(0.0, 0.08)),
            "description": "Net Profit / (Equity Capital + Reserves).",
        },
    ]

    return {"company_id": cid, "quarter": f.get("quarter"), "signals": signals}


@app.get("/company/{company_id}/history")
def get_score_history(company_id: str, years: int = Query(default=12, le=20)):
    
    cid = normalize_id(company_id)
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT quarter, hazard_probability, risk_tier, score_delta, red_signal_count
            FROM scores WHERE company_id=?
            ORDER BY quarter DESC LIMIT ?
        """, (cid, years)).fetchall()
    return {"company_id": cid, "history": [dict(r) for r in rows]}


@app.get("/alerts")
def get_recent_alerts(limit: int = Query(default=50, le=200), severity: str | None = None):
    with get_connection() as conn:
        if severity:
            rows = conn.execute("""
                SELECT company_id, signal, severity, message, created_at
                FROM alerts WHERE severity=?
                ORDER BY created_at DESC LIMIT ?
            """, (severity, limit)).fetchall()
        else:
            rows = conn.execute("""
                SELECT company_id, signal, severity, message, created_at
                FROM alerts
                ORDER BY created_at DESC LIMIT ?
            """, (limit,)).fetchall()
    return [dict(r) for r in rows]


@app.get("/search")
def search_companies(q: str = Query(min_length=1), limit: int = Query(default=20, le=100)):
 
    pattern = f"%{q.upper().replace(' ', '_')}%"
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT DISTINCT company_id FROM features
            WHERE company_id LIKE ?
            LIMIT ?
        """, (pattern, limit)).fetchall()
    return [r["company_id"] for r in rows]


@app.get("/stats")
def get_dataset_stats():
   
    with get_connection() as conn:
        n_companies = conn.execute("SELECT COUNT(DISTINCT company_id) FROM features").fetchone()[0]
        n_rows = conn.execute("SELECT COUNT(*) FROM features").fetchone()[0]
        n_distress = conn.execute("SELECT COUNT(*) FROM distress_labels WHERE distress=1").fetchone()[0]
        year_range = conn.execute("SELECT MIN(quarter), MAX(quarter) FROM features").fetchone()

    return {
        "total_companies": n_companies,
        "total_company_years": n_rows,
        "documented_distress_events": n_distress,
        "year_range": {"min": year_range[0], "max": year_range[1]},
        "note": (
            "Documented distress events are intentionally few (rare, well-"
            "verified public failures). Reported model metrics should be "
            "read as directional, not production-grade, given this sample size."
        ),
    }


@app.get("/pipeline/run")
def trigger_pipeline():
    from scheduler import run_weekly_pipeline
    import threading
    thread = threading.Thread(target=run_weekly_pipeline, daemon=True)
    thread.start()
    return {"status": "pipeline triggered", "message": "Running in background"}