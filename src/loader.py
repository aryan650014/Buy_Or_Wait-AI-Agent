import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = BASE_DIR / "dataset"


def load_csv(filename):
    file_path = DATASET_DIR / filename
    return pd.read_csv(file_path)


if __name__ == "__main__":
    requests = load_csv("requests.csv")
    profiles = load_csv("financial_profiles.csv")
    events = load_csv("financial_events.csv")

    print("Requests:", requests.shape)
    print("Profiles:", profiles.shape)
    print("Events:", events.shape)

    print("\nFirst Request:")
    print(requests.head(1).to_string(index=False))