from ingestion.kaggle_fetcher import get_dataset_root
import os

root = get_dataset_root()
companies = sorted(os.listdir(root))

print(f"Total companies: {len(companies)}")
print("\nFirst 30:")
for c in companies[:30]:
    print(f"  {c}")

print("\nLast 30:")
for c in companies[-30:]:
    print(f"  {c}")