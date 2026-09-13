from data_loader import load_data


data = load_data()
rates = data["exchange_rates"]


print("Total exchange rates:", len(rates))

print("\nCurrencies:")
currencies = sorted(
    set(rates["from_currency"]) |
    set(rates["to_currency"])
)
print(currencies)


print("\nDate range:")
print("From:", rates["rate_date"].min().date())
print("To:  ", rates["rate_date"].max().date())


print("\nRates per currency pair:")
print(
    rates
    .groupby(["from_currency", "to_currency"])
    .size()
    .sort_values(ascending=False)
    .to_string()
)