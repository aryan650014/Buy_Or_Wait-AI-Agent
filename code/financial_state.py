from data_loader import load_data
from event_resolver import get_user_events


def get_user_profile(profiles, user_id):
    profile = profiles[
        profiles["user_id"] == user_id
    ]

    if profile.empty:
        raise ValueError(
            f"Profile not found for {user_id}"
        )

    return profile.iloc[0]


def get_financial_state(
    data,
    user_id,
    request_date
):
    """
    Build the user's financial state
    on the request date.
    """

    profiles = data["financial_profiles"]
    events = data["financial_events"]

    profile = get_user_profile(
        profiles,
        user_id
    )

    user_events = get_user_events(
        events,
        user_id
    )

    historical_events = user_events[
        user_events["event_date"] <= request_date
    ].copy()

    future_events = user_events[
        user_events["event_date"] > request_date
    ].copy()

    return {
        "user_id": user_id,
        "request_date": request_date,

        "home_currency":
            profile["home_currency"],

        "current_available_balance":
            profile["current_available_balance"],

        "minimum_balance_to_keep":
            profile["minimum_balance_to_keep"],

        "financial_priorities":
            profile["financial_priorities"],

        "protected_categories":
            profile[
                "expense_categories_to_protect"
            ],

        "reducible_categories":
            profile[
                "expense_categories_user_is_willing_to_reduce"
            ],

        "stoppable_categories":
            profile[
                "expense_categories_user_is_willing_to_stop"
            ],

        "payment_methods":
            profile[
                "payment_methods_user_will_consider"
            ],

        "max_installment_months":
            profile[
                "max_installment_months"
            ],

        "historical_events":
            historical_events,

        "future_events":
            future_events,
    }


if __name__ == "__main__":

    data = load_data()

    request = data["requests"].iloc[0]

    state = get_financial_state(
        data=data,
        user_id=request["user_id"],
        request_date=request["request_date"]
    )

    print("Financial State")
    print("=" * 50)

    print(
        "User:",
        state["user_id"]
    )

    print(
        "Request date:",
        state["request_date"].date()
    )

    print(
        "Home currency:",
        state["home_currency"]
    )

    print(
        "Available balance:",
        state["current_available_balance"]
    )

    print(
        "Minimum balance:",
        state["minimum_balance_to_keep"]
    )

    print(
        "\nHistorical events:",
        len(state["historical_events"])
    )

    print(
        "Future events:",
        len(state["future_events"])
    )

    print("\nPayment methods:")
    print(
        state["payment_methods"]
    )

    print(
        "\nMax installment months:"
    )

    print(
        state["max_installment_months"]
    )