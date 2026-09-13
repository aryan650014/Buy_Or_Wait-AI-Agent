from loader import load_csv


files = [
    "requests.csv",
    "financial_profiles.csv",
    "financial_events.csv",
    "request_payment_options.csv",
    "messages.csv",
    "images.csv",
    "exchange_rates.csv"
]


for filename in files:
    print("\n" + "=" * 70)
    print(filename)
    print("=" * 70)

    df = load_csv(filename)

    print("Shape:", df.shape)
    print("Columns:")
    
    for column in df.columns:
        print(" -", column)