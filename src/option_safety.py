from datetime import timedelta
import pandas as pd

from currency_converter import CurrencyConverter
from payment_schedule import generate_payment_schedule


def is_within_installment_limit(
    option,
    max_installment_months
):
    """
    Check whether an installment plan finishes within
    the user's maximum allowed installment period.
    """

    if option["payment_method"] != "installments":
        return True

    if pd.isna(max_installment_months):
        return True

    schedule = generate_payment_schedule(option)

    if len(schedule) <= 1:
        return True

    first_date = schedule[0]["payment_date"]
    last_date = schedule[-1]["payment_date"]

    allowed_end_date = (
        first_date
        + pd.DateOffset(
            months=int(max_installment_months)
        )
    )

    return last_date <= allowed_end_date


def convert_payment_amount(
    payment_amount,
    payment_currency,
    payment_date,
    home_currency,
    currency_converter
):
    """
    Convert a payment amount into the user's home currency.
    """

    if pd.isna(payment_amount):
        raise ValueError(
            "Payment option contains a blank payment amount."
        )

    return currency_converter.convert(
        amount=float(payment_amount),
        from_currency=payment_currency,
        to_currency=home_currency,
        date=pd.Timestamp(payment_date)
    )


def check_payment_option_safety(
    starting_balance,
    minimum_balance,
    option,
    forecast_events,
    request_date,
    payment_currency,
    home_currency,
    currency_converter
):
    """
    Check whether a payment option remains safe when combined
    with all forecast financial events.

    Payment amounts are converted into home currency using
    the exchange rate for each payment date.
    """

    balance = float(starting_balance)

    schedule = generate_payment_schedule(option)

    timeline = []

    # --------------------------------------------------
    # Forecast events
    # --------------------------------------------------

    for event in forecast_events:

        if event["event_date"] < request_date:
            continue

        timeline.append({
            "date": pd.Timestamp(event["event_date"]),
            "amount": float(event["amount"]),
            "currency": event["currency"],
            "direction": event["direction"],
            "type": "forecast",
            "event_id": event.get("event_id"),
            "description": event.get("description"),
        })

    # --------------------------------------------------
    # Request payment schedule
    # --------------------------------------------------

    for payment in schedule:

        payment_date = pd.Timestamp(
            payment["payment_date"]
        )

        # Payment before request date is invalid.
        if payment_date < request_date:
            return False, []

        payment_amount_home = convert_payment_amount(
            payment_amount=payment["payment_amount"],
            payment_currency=payment_currency,
            payment_date=payment_date,
            home_currency=home_currency,
            currency_converter=currency_converter
        )

        timeline.append({
            "date": payment_date,
            "amount": payment_amount_home,
            "currency": home_currency,
            "direction": "debit",
            "type": "request_payment",
            "payment_number": payment["payment_number"],
            "original_amount": payment["payment_amount"],
            "original_currency": payment_currency,
        })

    # --------------------------------------------------
    # Sort complete timeline
    # --------------------------------------------------

    timeline.sort(
        key=lambda x: (
            x["date"],
            0 if x["type"] == "forecast" else 1
        )
    )

    results = []

    # --------------------------------------------------
    # Process timeline
    # --------------------------------------------------

    for event in timeline:

        if event["type"] == "forecast":

            converted_amount = convert_payment_amount(
                payment_amount=event["amount"],
                payment_currency=event["currency"],
                payment_date=event["date"],
                home_currency=home_currency,
                currency_converter=currency_converter
            )

        else:
            converted_amount = event["amount"]

        if event["direction"] == "credit":
            balance += converted_amount
        else:
            balance -= converted_amount

        result = {
            "date": event["date"],
            "amount": converted_amount,
            "currency": home_currency,
            "type": event["type"],
            "balance_after": balance,
            "below_minimum": (
                balance < minimum_balance
            ),
        }

        if event["type"] == "forecast":
            result["event_id"] = event.get("event_id")
            result["description"] = event.get(
                "description"
            )

        if event["type"] == "request_payment":
            result["payment_number"] = event.get(
                "payment_number"
            )
            result["original_amount"] = event.get(
                "original_amount"
            )
            result["original_currency"] = event.get(
                "original_currency"
            )

        results.append(result)

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

    request_id = "request_26"

    request = data["requests"][
        data["requests"]["request_id"] == request_id
    ].iloc[0]

    user_id = request["user_id"]

    profile = data["financial_profiles"][
        data["financial_profiles"]["user_id"] == user_id
    ].iloc[0]

    options = data["request_payment_options"][
        data["request_payment_options"]["request_id"]
        == request_id
    ]

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

    print()
    print("PAYMENT OPTION SAFETY TEST")
    print("=" * 70)

    print("Request:", request_id)
    print("User:", user_id)
    print("Home currency:", profile["home_currency"])
    print()

    for _, option in options.iterrows():

        safe, results = check_payment_option_safety(
            starting_balance=profile[
                "current_available_balance"
            ],
            minimum_balance=profile[
                "minimum_balance_to_keep"
            ],
            option=option,
            forecast_events=forecast_events,
            request_date=request["request_date"],
            payment_currency=profile["home_currency"],
            home_currency=profile["home_currency"],
            currency_converter=converter
        )

        lowest_balance = (
            min(
                result["balance_after"]
                for result in results
            )
            if results
            else profile["current_available_balance"]
        )

        print(
            option["payment_option_id"],
            "|",
            option["payment_method"],
            "|",
            "Amount:",
            option["payment_amount"],
            "|",
            "Payments:",
            int(option["number_of_payments"]),
            "|",
            "Safe:",
            safe,
            "|",
            "Lowest balance:",
            round(lowest_balance, 2)
        )