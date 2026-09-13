from currency_converter import CurrencyConverter


def convert_amount(
    amount,
    from_currency,
    home_currency,
    date,
    currency_converter
):
    """
    Convert an amount into the user's home currency.
    """

    if amount is None:
        raise ValueError(
            "Cannot convert a blank amount."
        )

    return currency_converter.convert(
        amount=float(amount),
        from_currency=from_currency,
        to_currency=home_currency,
        date=date
    )


def check_request_safety(
    starting_balance,
    minimum_balance,
    request_amount,
    request_currency,
    request_date,
    forecast_events,
    home_currency,
    currency_converter
):
    """
    Check whether a requested purchase is safe while
    considering the complete forecast.

    All amounts are converted into the user's home currency
    before balance calculations.
    """

    starting_balance = float(starting_balance)
    minimum_balance = float(minimum_balance)

    # --------------------------------------------------
    # Convert requested purchase
    # --------------------------------------------------

    request_amount_home = convert_amount(
        amount=request_amount,
        from_currency=request_currency,
        home_currency=home_currency,
        date=request_date,
        currency_converter=currency_converter
    )

    # Purchase happens on request_date
    balance = starting_balance - request_amount_home

    results = []

    results.append({
        "event_date": request_date,
        "description": "Requested purchase",
        "category": "request",
        "direction": "debit",
        "original_amount": request_amount,
        "original_currency": request_currency,
        "converted_amount": request_amount_home,
        "currency": home_currency,
        "balance_after": balance,
        "below_minimum": balance < minimum_balance,
    })

    # --------------------------------------------------
    # Process forecast events
    # --------------------------------------------------

    sorted_events = sorted(
        forecast_events,
        key=lambda x: x["event_date"]
    )

    for event in sorted_events:

        # Ignore events before the request date
        if event["event_date"] < request_date:
            continue

        converted_amount = convert_amount(
            amount=event["amount"],
            from_currency=event["currency"],
            home_currency=home_currency,
            date=event["event_date"],
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

    # --------------------------------------------------
    # Final safety check
    # --------------------------------------------------

    safe = all(
        not result["below_minimum"]
        for result in results
    )

    return safe, results


if __name__ == "__main__":

    from data_loader import load_data
    from event_resolver import get_user_events
    from forecast import generate_forecast

    data = load_data()

    user_id = "user_26"

    request = data["requests"][
        data["requests"]["request_id"] == "request_26"
    ].iloc[0]

    profile = data["financial_profiles"][
        data["financial_profiles"]["user_id"] == user_id
    ].iloc[0]

    user_events = get_user_events(
        data["financial_events"],
        user_id
    )

    forecast_events = generate_forecast(
        events=user_events,
        request_date=request["request_date"],
        days=90
    )

    converter = CurrencyConverter(
        data["exchange_rates"]
    )

    safe, results = check_request_safety(
        starting_balance=profile[
            "current_available_balance"
        ],
        minimum_balance=profile[
            "minimum_balance_to_keep"
        ],
        request_amount=request["requested_amount"],
        request_currency=profile["home_currency"],
        request_date=request["request_date"],
        forecast_events=forecast_events,
        home_currency=profile["home_currency"],
        currency_converter=converter
    )

    print()
    print("REQUEST SAFETY TEST")
    print("=" * 70)

    print("Request:", request["request_id"])
    print("User:", user_id)
    print(
        "Requested amount:",
        request["requested_amount"],
        profile["home_currency"]
    )

    print()
    print("Safe:", safe)

    if results:
        print()
        print(
            "Balance after request:",
            round(results[0]["balance_after"], 2),
            profile["home_currency"]
        )

        lowest_balance = min(
            result["balance_after"]
            for result in results
        )

        print(
            "Lowest forecast balance:",
            round(lowest_balance, 2),
            profile["home_currency"]
        )

        print(
            "Minimum required:",
            profile["minimum_balance_to_keep"],
            profile["home_currency"]
        )