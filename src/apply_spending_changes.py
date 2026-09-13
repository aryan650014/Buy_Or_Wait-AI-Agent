from data_loader import load_data
from event_resolver import get_user_events
from forecast import generate_forecast
from spending_changes import generate_spending_changes
from balance_forecast import calculate_balance_forecast
from spending_change_engine import apply_spending_changes


def main():

    data = load_data()

    # Test with first request
    request = data["requests"].iloc[0]
    user_id = request["user_id"]

    profile = data["financial_profiles"][
        data["financial_profiles"]["user_id"] == user_id
    ].iloc[0]

    # Get valid user events
    user_events = get_user_events(
        data["financial_events"],
        user_id
    )

    # Generate original forecast
    forecast_events = generate_forecast(
        events=user_events,
        request_date=request["request_date"],
        days=90
    )

    # Generate eligible spending changes
    spending_changes = generate_spending_changes(
        events=user_events,
        protected_categories=profile[
            "expense_categories_to_protect"
        ],
        max_changes=3
    )

    # Apply changes
    updated_forecast = apply_spending_changes(
        forecast_events,
        spending_changes
    )

    # Original forecast balance
    original_results = calculate_balance_forecast(
        starting_balance=profile["current_available_balance"],
        minimum_balance=profile["minimum_balance_to_keep"],
        forecast_events=forecast_events
    )

    # Updated forecast balance
    updated_results = calculate_balance_forecast(
        starting_balance=profile["current_available_balance"],
        minimum_balance=profile["minimum_balance_to_keep"],
        forecast_events=updated_forecast
    )

    original_lowest = min(
        result["balance_after"]
        for result in original_results
    )

    updated_lowest = min(
        result["balance_after"]
        for result in updated_results
    )

    print("Real Spending Change Test")
    print("=" * 70)

    print("User:", user_id)
    print("Request:", request["request_id"])

    print("\nSuggested Changes:")
    for change in spending_changes:
        print(" ", change)

    print("\nOriginal Lowest Balance:")
    print(f"  {original_lowest:,.2f}")

    print("\nUpdated Lowest Balance:")
    print(f"  {updated_lowest:,.2f}")

    print("\nBalance Improvement:")
    print(
        f"  {updated_lowest - original_lowest:,.2f}"
    )

    print("\nChanged Forecast Events:")
    for original, updated in zip(
        forecast_events,
        updated_forecast
    ):
        if original["amount"] != updated["amount"]:
            print(
                f"  {original['event_id']} | "
                f"{original['description']} | "
                f"{original['amount']:,.2f} -> "
                f"{updated['amount']:,.2f}"
            )


if __name__ == "__main__":
    main()