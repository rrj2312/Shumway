from database.db import get_connection
from ingestion.distress_labels import seed_distress_labels

conn = get_connection()
conn.execute("DELETE FROM distress_labels")
conn.commit()
print("Cleared old distress_labels")

seed_distress_labels()
print("Reseeded with annual-format labels")