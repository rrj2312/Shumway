from database.db import get_connection
import logging

log = logging.getLogger(__name__)

KNOWN_DISTRESS_EVENTS = [
    ("YESBANK_NS",    "2020", "moratorium",       "RBI imposed moratorium 5 March 2020"),
    ("RELCAPITAL_NS", "2022", "moratorium",       "RBI superseded Reliance Capital board Nov 2021"),
    ("SUZLON_NS",     "2015", "rating_downgrade", "CARE downgraded to D, restructuring 2015"),
    ("JETAIRWAYS_NS", "2019", "insolvency",       "Operations ceased April 2019, NCLT insolvency proceedings"),
    ("CGPOWER_NS",    "2019", "fraud_disclosure", "Accounting fraud and governance crisis disclosed August 2019"),
    ("FRETAIL_NS",    "2021", "default",          "Default on payments, insolvency proceedings initiated 2022 (FY2021 = latest available pre-event data)"),
]


def seed_distress_labels():
    with get_connection() as conn:
        for company_id, quarter, event_type, note in KNOWN_DISTRESS_EVENTS:
            conn.execute("""
                INSERT INTO distress_labels
                    (company_id, quarter, distress, event_type, source_note)
                VALUES (?, ?, 1, ?, ?)
                ON CONFLICT(company_id, quarter)
                DO UPDATE SET
                    distress=1,
                    event_type=excluded.event_type,
                    source_note=excluded.source_note
            """, (company_id, quarter, event_type, note))
    log.info(f"Seeded {len(KNOWN_DISTRESS_EVENTS)} distress labels")


if __name__ == "__main__":
    seed_distress_labels()