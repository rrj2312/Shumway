from database.db import get_connection
import logging

log = logging.getLogger(__name__)

KNOWN_DISTRESS_EVENTS = [
    ("YESBANK_NS",   "2020-Q4", "moratorium",        "RBI imposed moratorium 5 March 2020"),
    ("DHFL_NS",      "2019-Q3", "default",            "DHFL defaulted on NCD payments June 2019"),
    ("RELCAPITAL_NS","2021-Q3", "moratorium",         "RBI superseded Reliance Capital board Nov 2021"),
    ("SUZLON_NS",    "2015-Q1", "rating_downgrade",   "CARE downgraded to D, restructuring 2015"),
    ("ZEEL_NS",      "2023-Q3", "restructuring",      "Sony merger collapse, lender pressure"),
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