from itertools import combinations

from spending_changes import (
    get_changeable_recurring_expenses,
    build_change,
)
from spending_change_engine import apply_spending_changes
from request_safety import check_request_safety


def find_best_spending_changes(
    starting_balance,
    minimum_balance,
    requested_amount,
    request_currency,
    request_date,
    forecast_events,
    protected_categories,
    home_currency,
    currency_converter,
    max_changes=3,
):
    """
    Find the minimum spending changes required to make
    the requested purchase 90-day safe.

    If the purchase is already safe, returns [].
    """

    # --------------------------------------------------
    # First check: no changes at all
    # --------------------------------------------------

    safe_without_changes, _ = check_request_safety(
        starting_balance=starting_balance,
        minimum_balance=minimum_balance,
        request_amount=requested_amount,
        request_currency=request_currency,
        request_date=request_date,
        forecast_events=forecast_events,
        home_currency=home_currency,
        currency_converter=currency_converter,
    )

    if safe_without_changes:
        return [], forecast_events

    # --------------------------------------------------
    # Find eligible recurring expenses
    # --------------------------------------------------

    candidates = get_changeable_recurring_expenses(
        events=forecast_events,
        protected_categories=protected_categories,
    )

    # --------------------------------------------------
    # Remove candidates that cannot produce a change
    # --------------------------------------------------

    usable_candidates = []

    for candidate in candidates:

        change = build_change(candidate)

        if change is None:
            continue

        candidate = candidate.copy()
        candidate["change"] = change

        usable_candidates.append(candidate)

    if not usable_candidates:
        return [], forecast_events

    # --------------------------------------------------
    # Try 1 change, then 2, then 3
    # --------------------------------------------------

    max_changes = min(
        max_changes,
        len(usable_candidates)
    )

    best_changes = None
    best_forecast = None

    for number_of_changes in range(
        1,
        max_changes + 1
    ):

        safe_combinations = []

        for combination in combinations(
            usable_candidates,
            number_of_changes
        ):

            changes = [
                candidate["change"]
                for candidate in combination
            ]

            updated_forecast = (
                apply_spending_changes(
                    forecast_events,
                    changes
                )
            )

            safe, safety_results = (
                check_request_safety(
                    starting_balance=starting_balance,
                    minimum_balance=minimum_balance,
                    request_amount=requested_amount,
                    request_currency=request_currency,
                    request_date=request_date,
                    forecast_events=updated_forecast,
                    home_currency=home_currency,
                    currency_converter=currency_converter,
                )
            )

            if not safe:
                continue

            # Calculate estimated saving
            total_saving = 0.0

            for result in safety_results:
                pass

            for candidate in combination:

                if candidate["flexibility"] in [
                    "stoppable",
                    "reducible_or_stoppable",
                ]:
                    total_saving += candidate[
                        "average_amount"
                    ]

                elif (
                    candidate["flexibility"]
                    == "reducible"
                ):
                    minimum = candidate[
                        "minimum_allowed_amount"
                    ]

                    if minimum is not None:
                        total_saving += max(
                            0.0,
                            candidate[
                                "average_amount"
                            ]
                            - float(minimum)
                        )

            safe_combinations.append({
                "changes": changes,
                "forecast": updated_forecast,
                "saving": total_saving,
            })

        # --------------------------------------------------
        # As soon as a safe solution exists with N changes,
        # don't use N+1 changes.
        # --------------------------------------------------

        if safe_combinations:

            safe_combinations.sort(
                key=lambda x: x["saving"]
            )

            best = safe_combinations[0]

            best_changes = best["changes"]
            best_forecast = best["forecast"]

            return (
                best_changes,
                best_forecast
            )

    # No combination could make it safe
    return [], forecast_events


if __name__ == "__main__":

    from data_loader import load_data
    from event_resolver import get_user_events
    from forecast import generate_forecast
    from currency_converter import CurrencyConverter

    data = load_data()

    request_id = "request_26"

    request = data["requests"][
        data["requests"]["request_id"]
        == request_id
    ].iloc[0]

    user_id = request["user_id"]

    profile = data["financial_profiles"][
        data["financial_profiles"]["user_id"]
        == user_id
    ].iloc[0]

    events = get_user_events(
        data["financial_events"],
        user_id
    )

    forecast_events = generate_forecast(
        events=events,
        request_date=request["request_date"],
        days=90
    )

    converter = CurrencyConverter(
        data["exchange_rates"]
    )

    changes, updated_forecast = (
        find_best_spending_changes(
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
            protected_categories=profile[
                "expense_categories_to_protect"
            ],
            home_currency=profile[
                "home_currency"
            ],
            currency_converter=converter,
            max_changes=3,
        )
    )

    print()
    print("SPENDING CHANGE OPTIMIZER")
    print("=" * 70)

    print("Request:", request_id)
    print("User:", user_id)

    print()
    print("Recommended changes:")

    if changes:
        for change in changes:
            print(" ", change)
    else:
        print(" None")

    print()
    print(
        "Original forecast:",
        len(forecast_events)
    )

    print(
        "Updated forecast:",
        len(updated_forecast)
    )