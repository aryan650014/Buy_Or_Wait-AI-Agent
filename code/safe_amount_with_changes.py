from data_loader import load_data
from event_resolver import get_user_events
from forecast import generate_forecast
from spending_changes import generate_spending_changes
from spending_change_engine import apply_spending_changes
from safe_amount import calculate_amount_safe_to_pay
from currency_converter import CurrencyConverter


def calculate_safe_amount_with_changes(
    starting_balance,
    minimum_balance,
    requested_amount,
    request_currency,
    request_date,
    forecast_events,
    spending_changes,
    home_currency,
    currency_converter
):
    """
    Calculate the maximum amount that can safely be paid today
    after applying spending changes.
    """

    # Apply proposed spending changes
    updated_forecast = apply_spending_changes(
        forecast_events,
        spending_changes
    )

    # Calculate maximum safe payment
    safe_amount = calculate_amount_safe_to_pay(
        starting_balance=starting_balance,
        minimum_balance=minimum_balance,
        requested_amount=requested_amount,
        request_currency=request_currency,
        request_date=request_date,
        forecast_events=updated_forecast,
        home_currency=home_currency,
        currency_converter=currency_converter
    )

    return safe_amount, updated_forecast


if __name__ == "__main__":

    data = load_data()

    # --------------------------------------------------
    # Select test request
    # --------------------------------------------------

    request = data["requests"].iloc[0]

    request_id = request["request_id"]
    user_id = request["user_id"]

    # --------------------------------------------------
    # User profile
    # --------------------------------------------------

    profile = data["financial_profiles"][
        data["financial_profiles"]["user_id"] == user_id
    ].iloc[0]

    home_currency = profile["home_currency"]

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
    # 90-day forecast
    # --------------------------------------------------

    forecast_events = generate_forecast(
        events=user_events,
        request_date=request["request_date"],
        days=90
    )

    # --------------------------------------------------
    # Generate possible spending changes
    # --------------------------------------------------

    spending_changes = generate_spending_changes(
        events=user_events,
        protected_categories=profile[
            "expense_categories_to_protect"
        ],
        max_changes=3
    )

    # --------------------------------------------------
    # Calculate safe amount
    # --------------------------------------------------

    safe_amount, updated_forecast = (
        calculate_safe_amount_with_changes(
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

            request_date=request[
                "request_date"
            ],

            forecast_events=forecast_events,

            spending_changes=spending_changes,

            home_currency=home_currency,

            currency_converter=converter
        )
    )

    # --------------------------------------------------
    # Output
    # --------------------------------------------------

    print()
    print("SAFE AMOUNT WITH SPENDING CHANGES")
    print("=" * 70)

    print("User:", user_id)
    print("Request:", request_id)

    print(
        "Home Currency:",
        home_currency
    )

    print(
        "Requested Amount:",
        f"{request['requested_amount']:,.2f}"
    )

    print("\nSpending Changes:")

    if spending_changes:

        for change in spending_changes:
            print(" ", change)

    else:

        print(" None")

    print(
        "\nAmount Safe To Pay:",
        f"{safe_amount:,.2f}"
    )

    print(
        "\nForecast Events Before Changes:",
        len(forecast_events)
    )

    print(
        "Forecast Events After Changes:",
        len(updated_forecast)
    )