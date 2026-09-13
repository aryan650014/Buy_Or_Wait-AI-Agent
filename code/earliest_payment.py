from datetime import timedelta

import pandas as pd

from request_safety import check_request_safety
from currency_converter import CurrencyConverter


def find_earliest_full_payment_date(
    starting_balance,
    minimum_balance,
    requested_amount,
    request_currency,
    forecast_events,
    request_date,
    home_currency,
    currency_converter,
    days=90
):
    """
    Find the earliest date within the forecast period on which
    the full requested amount can safely be paid.

    This calculation is independent of the user's
    payment-method preferences.
    """

    request_date = pd.Timestamp(
        request_date
    ).normalize()

    # --------------------------------------------------
    # Check today first
    # --------------------------------------------------

    safe_today, _ = check_request_safety(
        starting_balance=starting_balance,
        minimum_balance=minimum_balance,
        request_amount=requested_amount,
        request_currency=request_currency,
        request_date=request_date,
        forecast_events=forecast_events,
        home_currency=home_currency,
        currency_converter=currency_converter,
    )

    if safe_today:
        return request_date

    # --------------------------------------------------
    # Check each future date
    # --------------------------------------------------

    for day in range(1, days + 1):

        candidate_date = (
            request_date
            + timedelta(days=day)
        )

        # Events occurring before or on candidate date
        events_until_date = [
            event
            for event in forecast_events
            if (
                pd.Timestamp(
                    event["event_date"]
                ).normalize()
                <= candidate_date
            )
        ]

        # --------------------------------------------------
        # Calculate balance before purchase
        # --------------------------------------------------

        balance = float(starting_balance)

        sorted_events = sorted(
            events_until_date,
            key=lambda x: x["event_date"]
        )

        safe_before_purchase = True

        for event in sorted_events:

            event_date = pd.Timestamp(
                event["event_date"]
            ).normalize()

            converted_amount = (
                currency_converter.convert(
                    amount=float(event["amount"]),
                    from_currency=event["currency"],
                    to_currency=home_currency,
                    date=event_date,
                )
            )

            if event["direction"] == "credit":
                balance += converted_amount
            else:
                balance -= converted_amount

            if balance < minimum_balance:
                safe_before_purchase = False
                break

        if not safe_before_purchase:
            continue

        # --------------------------------------------------
        # Convert requested amount to home currency
        # --------------------------------------------------

        requested_amount_home = (
            currency_converter.convert(
                amount=float(requested_amount),
                from_currency=request_currency,
                to_currency=home_currency,
                date=candidate_date,
            )
        )

        # --------------------------------------------------
        # Check purchase
        # --------------------------------------------------

        balance_after_purchase = (
            balance - requested_amount_home
        )

        if (
            balance_after_purchase
            >= minimum_balance
        ):
            return candidate_date

    # --------------------------------------------------
    # Not possible within 90 days
    # --------------------------------------------------

    return None


if __name__ == "__main__":

    from data_loader import load_data
    from event_resolver import get_user_events
    from forecast import generate_forecast

    data = load_data()

    # --------------------------------------------------
    # Test request
    # --------------------------------------------------

    request = data["requests"].iloc[0]

    request_id = request["request_id"]
    user_id = request["user_id"]

    # --------------------------------------------------
    # Profile
    # --------------------------------------------------

    profile = data["financial_profiles"][
        data["financial_profiles"]["user_id"]
        == user_id
    ].iloc[0]

    home_currency = profile[
        "home_currency"
    ]

    # --------------------------------------------------
    # Currency converter
    # --------------------------------------------------

    converter = CurrencyConverter(
        data["exchange_rates"]
    )

    # --------------------------------------------------
    # User events
    # --------------------------------------------------

    user_events = get_user_events(
        data["financial_events"],
        user_id
    )

    # --------------------------------------------------
    # Forecast
    # --------------------------------------------------

    forecast_events = generate_forecast(
        events=user_events,
        request_date=request[
            "request_date"
        ],
        days=90
    )

    # --------------------------------------------------
    # Earliest date
    # --------------------------------------------------

    earliest_date = (
        find_earliest_full_payment_date(
            starting_balance=profile[
                "current_available_balance"
            ],

            minimum_balance=profile[
                "minimum_balance_to_keep"
            ],

            requested_amount=request[
                "requested_amount"
            ],

            request_currency=home_currency,

            forecast_events=forecast_events,

            request_date=request[
                "request_date"
            ],

            home_currency=home_currency,

            currency_converter=converter,

            days=90
        )
    )

    # --------------------------------------------------
    # Output
    # --------------------------------------------------

    print()
    print("EARLIEST FULL PAYMENT")
    print("=" * 70)

    print("Request:", request_id)
    print("User:", user_id)

    print(
        "Requested Amount:",
        f"{request['requested_amount']:,.2f}",
        home_currency
    )

    if earliest_date is None:

        print(
            "Earliest Date:",
            "Not possible within 90 days"
        )

    else:

        print(
            "Earliest Date:",
            earliest_date.date()
        )