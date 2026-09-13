from currency_converter import CurrencyConverter
from request_safety import check_request_safety


def calculate_amount_safe_to_pay(
    starting_balance,
    minimum_balance,
    requested_amount,
    request_currency,
    request_date,
    forecast_events,
    home_currency,
    currency_converter
):
    """
    Calculate the maximum amount that can safely be paid today.

    The requested amount is expressed in request_currency,
    while the user's balance is maintained in home_currency.

    Binary search is used to find the maximum safe amount.
    """

    requested_amount = float(requested_amount)

    # --------------------------------------------------
    # Fast check: can the full requested amount be paid?
    # --------------------------------------------------

    safe_full, _ = check_request_safety(
        starting_balance=starting_balance,
        minimum_balance=minimum_balance,
        request_amount=requested_amount,
        request_currency=request_currency,
        request_date=request_date,
        forecast_events=forecast_events,
        home_currency=home_currency,
        currency_converter=currency_converter
    )

    if safe_full:
        return round(requested_amount, 2)

    # --------------------------------------------------
    # Binary search
    # --------------------------------------------------

    low = 0.0
    high = requested_amount

    for _ in range(60):

        mid = (low + high) / 2

        safe, _ = check_request_safety(
            starting_balance=starting_balance,
            minimum_balance=minimum_balance,
            request_amount=mid,
            request_currency=request_currency,
            request_date=request_date,
            forecast_events=forecast_events,
            home_currency=home_currency,
            currency_converter=currency_converter
        )

        if safe:
            low = mid
        else:
            high = mid

    return round(low, 2)


if __name__ == "__main__":

    from data_loader import load_data
    from event_resolver import get_user_events
    from forecast import generate_forecast

    data = load_data()

    request_id = "request_26"

    request = data["requests"][
        data["requests"]["request_id"] == request_id
    ].iloc[0]

    user_id = request["user_id"]

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

    safe_amount = calculate_amount_safe_to_pay(
        starting_balance=profile[
            "current_available_balance"
        ],
        minimum_balance=profile[
            "minimum_balance_to_keep"
        ],
        requested_amount=request[
            "requested_amount"
        ],
        request_currency=profile[
            "home_currency"
        ],
        request_date=request[
            "request_date"
        ],
        forecast_events=forecast_events,
        home_currency=profile[
            "home_currency"
        ],
        currency_converter=converter
    )

    print()
    print("SAFE AMOUNT TEST")
    print("=" * 70)

    print("Request:", request_id)
    print("User:", user_id)

    print(
        "Requested amount:",
        request["requested_amount"],
        profile["home_currency"]
    )

    print(
        "Amount safe to pay:",
        safe_amount,
        profile["home_currency"]
    )

    print(
        "Amount remaining:",
        round(
            request["requested_amount"]
            - safe_amount,
            2
        ),
        profile["home_currency"]
    )