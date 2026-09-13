import pandas as pd
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = BASE_DIR / "dataset"


def load_data():
    data = {}

    files = [
        "requests",
        "financial_profiles",
        "financial_events",
        "request_payment_options",
        "messages",
        "images",
        "exchange_rates",
    ]

    for filename in files:
        path = DATASET_DIR / f"{filename}.csv"
        data[filename] = pd.read_csv(path)

    # Convert date columns
    data["requests"]["request_date"] = pd.to_datetime(
        data["requests"]["request_date"]
    )

    data["requests"]["desired_completion_date"] = pd.to_datetime(
        data["requests"]["desired_completion_date"]
    )

    data["financial_events"]["event_date"] = pd.to_datetime(
        data["financial_events"]["event_date"]
    )

    data["financial_events"]["settlement_date"] = pd.to_datetime(
        data["financial_events"]["settlement_date"]
    )

    data["request_payment_options"]["first_payment_date"] = pd.to_datetime(
        data["request_payment_options"]["first_payment_date"]
    )

    data["messages"]["sent_at"] = pd.to_datetime(
        data["messages"]["sent_at"]
    )

    data["exchange_rates"]["rate_date"] = pd.to_datetime(
        data["exchange_rates"]["rate_date"]
    )

    return data


if __name__ == "__main__":
    data = load_data()

    print("Data loaded successfully!\n")

    for name, df in data.items():
        print(f"{name}: {df.shape}")

    print("\nRequest date type:")
    print(data["requests"]["request_date"].dtype)

    print("\nEvent date type:")
    print(data["financial_events"]["event_date"].dtype)