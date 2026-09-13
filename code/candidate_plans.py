import pandas as pd

from event_resolver import get_user_events
from forecast import generate_forecast
from payment_schedule import generate_payment_schedule
from preference_checker import get_user_payment_preferences
from option_safety import (
    check_payment_option_safety,
    is_within_installment_limit,
)


def get_candidate_plans(data, request_id, user_id):

    requests = data["requests"]
    profiles = data["financial_profiles"]
    options = data["request_payment_options"]

    # --------------------------------------------------
    # Get request
    # --------------------------------------------------

    request_rows = requests[
        requests["request_id"] == request_id
    ]

    if request_rows.empty:
        raise ValueError(
            f"Request not found: {request_id}"
        )

    request = request_rows.iloc[0]

    # --------------------------------------------------
    # Get user profile
    # --------------------------------------------------

    profile_rows = profiles[
        profiles["user_id"] == user_id
    ]

    if profile_rows.empty:
        raise ValueError(
            f"Profile not found for {user_id}"
        )

    profile = profile_rows.iloc[0]

    # --------------------------------------------------
    # User financial events
    # --------------------------------------------------

    user_events = get_user_events(
        data["financial_events"],
        user_id
    )

    # --------------------------------------------------
    # Generate 90-day forecast
    # --------------------------------------------------

    forecast_events = generate_forecast(
        events=user_events,
        request_date=request["request_date"],
        days=90
    )

    # --------------------------------------------------
    # Payment preferences
    # --------------------------------------------------

    preferences = get_user_payment_preferences(
        profiles,
        user_id
    )

    # --------------------------------------------------
    # Request payment options
    # --------------------------------------------------

    request_options = options[
        options["request_id"] == request_id
    ].copy()

    candidates = []

    # --------------------------------------------------
    # Evaluate every payment option
    # --------------------------------------------------

    for _, option in request_options.iterrows():

        method = str(
            option["payment_method"]
        ).strip().lower()

        # ----------------------------------------------
        # 1. Payment method preference
        # ----------------------------------------------

        if method not in preferences:
            continue

        # ----------------------------------------------
        # 2. Generate exact payment schedule
        # ----------------------------------------------

        schedule = generate_payment_schedule(
            option
        )

        if not schedule:
            continue

        first_payment_date = pd.Timestamp(
            schedule[0]["payment_date"]
        )

        final_payment_date = pd.Timestamp(
            schedule[-1]["payment_date"]
        )

        request_date = pd.Timestamp(
            request["request_date"]
        )

        desired_completion_date = pd.Timestamp(
            request["desired_completion_date"]
        )

        # ----------------------------------------------
        # 3. No payment before request date
        # ----------------------------------------------

        if first_payment_date < request_date:
            continue

        # ----------------------------------------------
        # 4. Deadline check
        # ----------------------------------------------

        completes_by_deadline = (
            final_payment_date
            <= desired_completion_date
        )

        if not completes_by_deadline:
            continue

        # ----------------------------------------------
        # 5. Installment duration check
        # ----------------------------------------------

        if not is_within_installment_limit(
            option=option,
            max_installment_months=profile[
                "max_installment_months"
            ],
        ):
            continue

        # ----------------------------------------------
        # 6. Payment option safety
        # ----------------------------------------------

        safety_ok, safety_results = (
            check_payment_option_safety(
                starting_balance=profile[
                    "current_available_balance"
                ],
                minimum_balance=profile[
                    "minimum_balance_to_keep"
                ],
                option=option,
                forecast_events=forecast_events,
                request_date=request_date,
                payment_currency=profile[
                    "home_currency"
                ],
                home_currency=profile[
                    "home_currency"
                ],
                currency_converter=(
                    __import__(
                        "currency_converter"
                    ).CurrencyConverter(
                        data["exchange_rates"]
                    )
                ),
            )
        )

        if not safety_ok:
            continue

        # ----------------------------------------------
        # 7. Lowest balance
        # ----------------------------------------------

        if safety_results:

            lowest_balance = min(
                result["balance_after"]
                for result in safety_results
            )

        else:

            lowest_balance = profile[
                "current_available_balance"
            ]

        # ----------------------------------------------
        # 8. Candidate plan
        # ----------------------------------------------

        candidates.append({

            "payment_option_id":
                option["payment_option_id"],

            "payment_method":
                method,

            "payment_amount":
                float(option["payment_amount"]),

            "number_of_payments":
                int(option["number_of_payments"]),

            "first_payment_date":
                first_payment_date,

            "final_payment_date":
                final_payment_date,

            "payment_frequency_days":
                option[
                    "payment_frequency_days"
                ],

            "financing_fee":
                float(option["financing_fee"]),

            "total_payable_amount":
                float(option[
                    "total_payable_amount"
                ]),

            "lowest_balance":
                float(lowest_balance),

            "completes_by_deadline":
                completes_by_deadline,

            "spending_changes_count":
                0,

            "spending_changes":
                [],

            "schedule":
                schedule,
        })

    return candidates


# ======================================================
# TEST
# ======================================================

if __name__ == "__main__":

    from data_loader import load_data

    data = load_data()

    request_id = "request_26"

    request = data["requests"][
        data["requests"]["request_id"]
        == request_id
    ].iloc[0]

    user_id = request["user_id"]

    candidates = get_candidate_plans(
        data=data,
        request_id=request_id,
        user_id=user_id
    )

    print()
    print("CANDIDATE PLAN TEST")
    print("=" * 70)

    print("Request:", request_id)
    print("User:", user_id)

    print()
    print(
        "Total safe candidate plans:",
        len(candidates)
    )

    print()

    for plan in candidates:

        print(
            plan["payment_option_id"],
            "|",
            plan["payment_method"],
            "|",
            "Amount:",
            plan["payment_amount"],
            "|",
            "Payments:",
            plan["number_of_payments"],
            "|",
            "First:",
            plan["first_payment_date"].date(),
            "|",
            "Final:",
            plan["final_payment_date"].date(),
            "|",
            "Total:",
            plan["total_payable_amount"],
            "|",
            "Lowest:",
            round(
                plan["lowest_balance"],
                2
            )
        )