from currency_converter import CurrencyConverter


def convert_event_amount(
    event,
    home_currency,
    currency_converter
):
    """
    Convert an event amount into the user's home currency.
    """

    amount = event["amount"]

    if amount is None:
        raise ValueError(
            f"Blank amount found for event "
            f"{event['event_id']}"
        )

    return currency_converter.convert(
        amount=amount,
        from_currency=event["currency"],
        to_currency=home_currency,
        date=event["event_date"]
    )


def calculate_balance_forecast(
    starting_balance,
    minimum_balance,
    forecast_events,
    home_currency,
    currency_converter
):
    """
    Calculate the balance throughout the forecast period.

    Every event is converted into the user's home currency
    before being added/subtracted.
    """

    balance = float(starting_balance)
    results = []

    sorted_events = sorted(
        forecast_events,
        key=lambda x: x["event_date"]
    )

    for event in sorted_events:

        converted_amount = convert_event_amount(
            event=event,
            home_currency=home_currency,
            currency_converter=currency_converter
        )

        if event["direction"] == "credit":
            balance += converted_amount
        else:
            balance -= converted_amount

        results.append({
            "event_date": event["event_date"],
            "description": event["description"],
            "category": event["category"],
            "direction": event["direction"],
            "original_amount": event["amount"],
            "original_currency": event["currency"],
            "converted_amount": converted_amount,
            "currency": home_currency,
            "balance_after": balance,
            "below_minimum": balance < minimum_balance,
        })

    return results


def is_90_day_safe(
    starting_balance,
    minimum_balance,
    forecast_events,
    home_currency,
    currency_converter
):
    """
    Check whether the complete 90-day forecast remains
    above the user's minimum required balance.
    """

    results = calculate_balance_forecast(
        starting_balance=starting_balance,
        minimum_balance=minimum_balance,
        forecast_events=forecast_events,
        home_currency=home_currency,
        currency_converter=currency_converter
    )

    for result in results:
        if result["below_minimum"]:
            return False, results

    return True, results


if __name__ == "__main__":

    from data_loader import load_data
    from event_resolver import get_user_events
    from forecast import generate_forecast

    data = load_data()

    user_id = "user_26"
    request_date = data["requests"][
        data["requests"]["user_id"] == user_id
    ]["request_date"].iloc[0]

    profile = data["financial_profiles"][
        data["financial_profiles"]["user_id"] == user_id
    ].iloc[0]

    home_currency = profile["home_currency"]

    user_events = get_user_events(
        data["financial_events"],
        user_id
    )

    forecast_events = generate_forecast(
        events=user_events,
        request_date=request_date,
        days=90
    )

    converter = CurrencyConverter(
        data["exchange_rates"]
    )

    results = calculate_balance_forecast(
        starting_balance=profile[
            "current_available_balance"
        ],
        minimum_balance=profile[
            "minimum_balance_to_keep"
        ],
        forecast_events=forecast_events,
        home_currency=home_currency,
        currency_converter=converter
    )

    print()
    print("CURRENCY-AWARE BALANCE FORECAST TEST")
    print("=" * 70)

    print("User:", user_id)
    print("Home currency:", home_currency)
    print("Forecast events:", len(results))
    print()

    if results:

        for result in results:
            print(
                result["event_date"].date(),
                "|",
                result["description"],
                "|",
                result["original_amount"],
                result["original_currency"],
                "->",
                round(result["converted_amount"], 2),
                home_currency,
                "| Balance:",
                round(result["balance_after"], 2)
            )

        lowest_balance = min(
            result["balance_after"]
            for result in results
        )

        print()
        print(
            "Lowest balance:",
            round(lowest_balance, 2),
            home_currency
        )

        print(
            "Minimum required:",
            profile["minimum_balance_to_keep"],
            home_currency
        )

        print(
            "90-day safe:",
            all(
                not result["below_minimum"]
                for result in results
            )
        )

    else:
        print("No forecast events found.")