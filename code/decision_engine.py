import re
import pandas as pd

from data_loader import load_data
from financial_state import get_financial_state
from forecast import generate_forecast
from currency_converter import CurrencyConverter
from safe_amount import calculate_amount_safe_to_pay
from spending_changes import generate_spending_changes
from safe_amount_with_changes import calculate_safe_amount_with_changes
from earliest_payment import find_earliest_full_payment_date
from payment_options import get_request_payment_options
from option_safety import (
    check_payment_option_safety,
    is_within_installment_limit,
)
from payment_schedule import generate_payment_schedule


VALID_STATUSES = {
    "affordable_now",
    "affordable_with_plan",
    "affordable_later",
    "not_affordable",
}

VALID_PAYMENT_METHODS = {
    "full_payment",
    "partial_payment",
    "installments",
    "wait",
    "not_recommended",
}


def extract_request_currency(request_text):
    """
    Extract currency code from request text.
    Supported currencies in the dataset.
    """
    text = str(request_text).upper()

    currencies = ["INR", "IDR", "EUR", "ZAR", "USD"]

    for currency in currencies:
        if re.search(rf"\b{currency}\b", text):
            return currency

    raise ValueError(
        f"Could not determine currency from request text: {request_text}"
    )


def clean_value(value):
    """
    Convert pandas NaN/NaT to None.
    """
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    return value


def format_amount(value):
    return f"{float(value):.2f}"


def build_single_payment_plan(payment_date, amount):
    """
    Format:
    YYYY-MM-DD:amount
    """
    if payment_date is None:
        return "none"

    payment_date = pd.Timestamp(payment_date).normalize()

    return (
        f"{payment_date.strftime('%Y-%m-%d')}:"
        f"{float(amount):.2f}"
    )


def build_installment_payment_plan(option):
    """
    Generate chronological installment plan.
    """
    schedule = generate_payment_schedule(option)

    if not schedule:
        return "none"

    parts = []

    for payment in schedule:
        payment_date = pd.Timestamp(
            payment["payment_date"]
        ).normalize()

        amount = float(payment["payment_amount"])

        parts.append(
            f"{payment_date.strftime('%Y-%m-%d')}:{amount:.2f}"
        )

    return "|".join(parts)


def format_spending_changes(changes):
    """
    Convert spending changes into required output format.
    """

    if not changes:
        return "none"

    formatted_changes = []

    for change in changes:

        # If already formatted as string
        if isinstance(change, str):
            formatted_changes.append(change)
            continue

        # If dictionary
        if not isinstance(change, dict):
            continue

        action = str(
            change.get("action", "")
        ).strip().lower()

        event_id = str(
            change.get("event_id", "")
        ).strip()

        amount = change.get(
            "amount",
            change.get("target_amount", None)
        )

        if not event_id:
            continue

        if action == "stop":
            formatted_changes.append(
                f"stop:{event_id}"
            )

        elif action == "reduce_to":
            if amount is not None:
                formatted_changes.append(
                    f"reduce_to:{event_id}:{float(amount):.2f}"
                )

    if not formatted_changes:
        return "none"

    return "|".join(formatted_changes[:3])

def partial_payment_allowed(state, request):
    methods = str(
        state["payment_methods"]
    ).lower()

    profile_allows = (
        "partial_payment" in methods
    )

    request_allows = bool(
        request.get(
            "allows_partial_payment",
            False
        )
    )

    return (
        profile_allows
        or request_allows
    )

def build_partial_payment_plan(
    safe_amount,
    requested_amount,
    request_date,
    earliest_full_payment_date,
):
    """
    Partial payment must contain exactly two payments:

    1. Safe amount today
    2. Remaining amount on earliest full-payment date
    """

    safe_amount = float(safe_amount)
    requested_amount = float(requested_amount)

    if safe_amount <= 0:
        return None

    if safe_amount >= requested_amount:
        return None

    if earliest_full_payment_date is None:
        return None

    request_date = pd.Timestamp(
        request_date
    ).normalize()

    earliest_date = pd.Timestamp(
        earliest_full_payment_date
    ).normalize()

    if earliest_date < request_date:
        return None

    remaining_amount = (
        requested_amount - safe_amount
    )

    if remaining_amount <= 0:
        return None

    return (
        f"{request_date.strftime('%Y-%m-%d')}:"
        f"{safe_amount:.2f}|"
        f"{earliest_date.strftime('%Y-%m-%d')}:"
        f"{remaining_amount:.2f}"
    )


def analyze_request(request, data):
    """
    Main deterministic financial decision engine.

    Financial affordability is calculated by Python.
    The output is validated against the hackathon rules.
    """

    request_id = request["request_id"]
    user_id = request["user_id"]

    request_date = pd.Timestamp(
        request["request_date"]
    ).normalize()

    requested_amount = float(
        request["requested_amount"]
    )

    request_currency = extract_request_currency(
        request["request_text"]
    )

    # =========================================================
    # 1. FINANCIAL STATE
    # =========================================================

    state = get_financial_state(
        data=data,
        user_id=user_id,
        request_date=request_date,
    )

    home_currency = str(
        state["home_currency"]
    ).strip().upper()

    currency_converter = CurrencyConverter(
        data["exchange_rates"]
    )

    # =========================================================
    # 2. 90-DAY FORECAST
    # =========================================================

    forecast_events = generate_forecast(
        events=state["historical_events"],
        request_date=request_date,
        days=90,
    )

    # =========================================================
    # 3. SAFE AMOUNT WITHOUT SPENDING CHANGES
    # =========================================================

    safe_amount_without_changes = (
        calculate_amount_safe_to_pay(
            starting_balance=state[
                "current_available_balance"
            ],
            minimum_balance=state[
                "minimum_balance_to_keep"
            ],
            requested_amount=requested_amount,
            request_currency=request_currency,
            request_date=request_date,
            forecast_events=forecast_events,
            home_currency=home_currency,
            currency_converter=currency_converter,
        )
    )

    # =========================================================
    # 4. FIND POSSIBLE SPENDING CHANGES
    #
    # IMPORTANT:
    # Actual signature is:
    #
    # generate_spending_changes(
    #     events,
    #     protected_categories,
    #     max_changes=3
    # )
    # =========================================================

    spending_changes = generate_spending_changes(
        events=state["historical_events"],
        protected_categories=state[
            "protected_categories"
        ],
        max_changes=3,
    )

    # =========================================================
    # 5. SAFE AMOUNT WITH SPENDING CHANGES
    # =========================================================

    try:

        safe_amount_with_changes, updated_forecast = (
            calculate_safe_amount_with_changes(
                starting_balance=state[
                    "current_available_balance"
                ],
                minimum_balance=state[
                    "minimum_balance_to_keep"
                ],
                requested_amount=requested_amount,
                request_currency=request_currency,
                request_date=request_date,
                forecast_events=forecast_events,
                home_currency=home_currency,
                currency_converter=currency_converter,
                spending_changes=spending_changes,
            )
        )

    except Exception:

        safe_amount_with_changes = (
            safe_amount_without_changes
        )

        updated_forecast = forecast_events

    # =========================================================
    # 6. FINAL SAFE AMOUNT
    # =========================================================

    safe_amount = max(
        float(safe_amount_without_changes),
        float(safe_amount_with_changes),
    )

    safe_amount = min(
        max(safe_amount, 0.0),
        requested_amount,
    )

    safe_amount = round(
        safe_amount,
        2,
    )

    # =========================================================
    # 7. FULL PAYMENT TODAY?
    # =========================================================

    full_payment_now = (
        safe_amount_without_changes
        >= requested_amount - 0.01
    )

    full_payment_after_changes = (
        safe_amount_with_changes
        >= requested_amount - 0.01
    )

    # =========================================================
    # 8. EARLIEST FULL PAYMENT DATE
    # =========================================================

    earliest_full_payment_date = (
        find_earliest_full_payment_date(
            starting_balance=state[
                "current_available_balance"
            ],
            minimum_balance=state[
                "minimum_balance_to_keep"
            ],
            requested_amount=requested_amount,
            request_currency=request_currency,
            request_date=request_date,
            forecast_events=forecast_events,
            home_currency=home_currency,
            currency_converter=currency_converter,
        )
    )

    # =========================================================
    # 9. DESIRED COMPLETION DATE
    # =========================================================

    desired_completion_date = clean_value(
        request["desired_completion_date"]
    )

    if desired_completion_date is not None:

        desired_completion_date = pd.Timestamp(
            desired_completion_date
        ).normalize()

    # =========================================================
    # 10. PAYMENT OPTIONS
    # =========================================================

    payment_options = get_request_payment_options(
        data["request_payment_options"],
        request_id,
    )

    valid_options = []

    max_installment_months = clean_value(
        state["max_installment_months"]
    )

    profile_methods = str(
        state["payment_methods"]
    ).lower()

    for _, option in payment_options.iterrows():

        option_type = str(
            option["payment_method"]
       ).strip().lower()

        # -----------------------------------------------------
        # User payment-method preference
        # -----------------------------------------------------

        if option_type:

            if option_type not in profile_methods:

                continue

        # -----------------------------------------------------
        # Installment month limit
        # -----------------------------------------------------

        if option_type == "installments":

            if max_installment_months is not None:

                if not is_within_installment_limit(
                    option,
                    max_installment_months,
                ):
                    continue

        # -----------------------------------------------------
        # First payment date
        # -----------------------------------------------------

        first_payment_date = clean_value(
            option.get("first_payment_date")
        )

        if first_payment_date is None:
            continue

        first_payment_date = pd.Timestamp(
            first_payment_date
        ).normalize()

        if first_payment_date < request_date:
            continue

        # -----------------------------------------------------
        # Deadline
        # -----------------------------------------------------

        if (
            desired_completion_date is not None
            and option_type == "installments"
        ):

            schedule = generate_payment_schedule(
                option
            )

            if schedule:

                final_date = pd.Timestamp(
                    schedule[-1]["payment_date"]
                ).normalize()

                if final_date > desired_completion_date:
                    continue

        # -----------------------------------------------------
        # Safety
        # -----------------------------------------------------

        try:

            option_safe, option_results = (
                check_payment_option_safety(
                    starting_balance=state[
                        "current_available_balance"
                    ],
                    minimum_balance=state[
                        "minimum_balance_to_keep"
                    ],
                    request_date=request_date,
                    request_amount=requested_amount,
                    request_currency=request_currency,
                    option=option,
                    forecast_events=forecast_events,
                    home_currency=home_currency,
                    currency_converter=currency_converter,
                )
            )

        except Exception:

            continue

        if option_safe:

            valid_options.append(
                {
                    "option": option,
                    "option_type": option_type,
                    "results": option_results,
                }
            )

    # =========================================================
    # 11. SELECT BEST PAYMENT OPTION
    # =========================================================

    selected_option = None

    if valid_options:

        priority = {
            "full_payment": 1,
            "partial_payment": 2,
            "installments": 3,
        }

        valid_options.sort(
            key=lambda item: (
                priority.get(
                    item["option_type"],
                    99,
                ),
                pd.Timestamp(
                    item["option"]["first_payment_date"]
                ),
            )
        )

        selected_option = valid_options[0]

    # =========================================================
    # 12. DEFAULT DECISION
    # =========================================================

    affordability_status = (
        "not_affordable"
    )

    recommended_payment_method = (
        "not_recommended"
    )

    payment_plan = "none"

    # =========================================================
    # CASE 1:
    # AFFORDABLE NOW
    # =========================================================

    if full_payment_now:

        affordability_status = (
            "affordable_now"
        )

        # Prefer actual full-payment option
        full_option = None

        for candidate in valid_options:

            if candidate["option_type"] == "full_payment":

                full_option = candidate
                break

        if full_option is not None:

            recommended_payment_method = (
                "full_payment"
            )

            payment_plan = build_single_payment_plan(
                request_date,
                requested_amount,
            )

        else:

            recommended_payment_method = (
                "full_payment"
            )

            payment_plan = build_single_payment_plan(
                request_date,
                requested_amount,
            )

    # =========================================================
    # CASE 2:
    # AFFORDABLE WITH SPENDING CHANGES
    # =========================================================

    elif full_payment_after_changes:

        affordability_status = (
            "affordable_with_plan"
        )

        recommended_payment_method = (
            "full_payment"
        )

        payment_plan = build_single_payment_plan(
            request_date,
            requested_amount,
        )

    # =========================================================
    # CASE 3:
    # INSTALLMENTS
    # =========================================================

    elif selected_option is not None:

        option_type = selected_option[
            "option_type"
        ]

        if option_type == "installments":

            affordability_status = (
                "affordable_with_plan"
            )

            recommended_payment_method = (
                "installments"
            )

            payment_plan = (
                build_installment_payment_plan(
                    selected_option["option"]
                )
            )

        elif option_type == "full_payment":

            affordability_status = (
                "affordable_with_plan"
            )

            recommended_payment_method = (
                "full_payment"
            )

            payment_plan = (
                build_single_payment_plan(
                    selected_option["option"][
                        "first_payment_date"
                    ],
                    requested_amount,
                )
            )

    # =========================================================
    # CASE 4:
    # PARTIAL PAYMENT
    # =========================================================

    elif partial_payment_allowed(
        state,
        request,
    ):

        if (
            safe_amount > 0
            and safe_amount < requested_amount
            and earliest_full_payment_date is not None
        ):

            earliest_date = pd.Timestamp(
                earliest_full_payment_date
            ).normalize()

            deadline_ok = (
                desired_completion_date is None
                or earliest_date <= desired_completion_date
            )

            if deadline_ok:

                partial_plan = (
                    build_partial_payment_plan(
                        safe_amount=safe_amount,
                        requested_amount=requested_amount,
                        request_date=request_date,
                        earliest_full_payment_date=earliest_date,
                    )
                )

                if partial_plan is not None:

                    affordability_status = (
                        "affordable_with_plan"
                    )

                    recommended_payment_method = (
                        "partial_payment"
                    )

                    payment_plan = (
                        partial_plan
                    )

    # =========================================================
    # CASE 5:
    # AFFORDABLE LATER
    # =========================================================

    if (
        affordability_status
        == "not_affordable"
        and earliest_full_payment_date is not None
    ):

        earliest_date = pd.Timestamp(
            earliest_full_payment_date
        ).normalize()

        deadline_ok = (
            desired_completion_date is None
            or earliest_date <= desired_completion_date
        )

        if (
            deadline_ok
            and earliest_date > request_date
        ):

            affordability_status = (
                "affordable_later"
            )

            recommended_payment_method = (
                "wait"
            )

            payment_plan = (
                build_single_payment_plan(
                    earliest_date,
                    requested_amount,
                )
            )

    # =========================================================
    # CASE 6:
    # NOT AFFORDABLE
    # =========================================================

    if (
        affordability_status
        == "not_affordable"
    ):

        recommended_payment_method = (
            "not_recommended"
        )

        payment_plan = "none"

    # =========================================================
    # 13. SPENDING CHANGES
    # =========================================================

    final_spending_changes = []

    if (
        full_payment_after_changes
        and not full_payment_now
    ):

        final_spending_changes = (
            spending_changes
        )

    # =========================================================
    # 14. DECISION EXPLANATION
    # =========================================================

    if (
        affordability_status
        == "affordable_now"
    ):

        explanation = (
            f"The requested amount of "
            f"{requested_amount:.2f} "
            f"{request_currency} is affordable now "
            f"without breaching the user's minimum "
            f"balance. Recommended method: "
            f"{recommended_payment_method}."
        )

    elif (
        affordability_status
        == "affordable_with_plan"
    ):

        if (
            recommended_payment_method
            == "installments"
        ):

            explanation = (
                f"The requested amount of "
                f"{requested_amount:.2f} "
                f"{request_currency} can be handled "
                f"through the available installment "
                f"plan while maintaining the user's "
                f"minimum balance."
            )

        elif (
            recommended_payment_method
            == "partial_payment"
        ):

            explanation = (
                f"The full amount of "
                f"{requested_amount:.2f} "
                f"{request_currency} cannot be safely "
                f"paid today, but a partial payment "
                f"followed by the remaining balance "
                f"is feasible."
            )

        else:

            explanation = (
                f"The requested amount of "
                f"{requested_amount:.2f} "
                f"{request_currency} becomes affordable "
                f"with the recommended spending changes "
                f"while maintaining the user's minimum "
                f"balance."
            )

    elif (
        affordability_status
        == "affordable_later"
    ):

        if earliest_full_payment_date is not None:

            explanation = (
                f"The requested amount of "
                f"{requested_amount:.2f} "
                f"{request_currency} is not safe "
                f"to pay today, but the forecast "
                f"indicates that full payment can "
                f"be made on "
                f"{pd.Timestamp(earliest_full_payment_date).strftime('%Y-%m-%d')} "
                f"without breaching the user's "
                f"minimum balance."
            )

        else:

            explanation = (
                f"The requested amount of "
                f"{requested_amount:.2f} "
                f"{request_currency} is not safe "
                f"to pay today."
            )

    else:

        explanation = (
            f"The requested amount of "
            f"{requested_amount:.2f} "
            f"{request_currency} cannot be safely "
            f"paid within the available forecast "
            f"and payment options without breaching "
            f"the user's minimum balance."
        )

    # =========================================================
    # 15. FINAL VALIDATION
    # =========================================================

    safe_amount = min(
        max(
            float(safe_amount),
            0.0,
        ),
        requested_amount,
    )

    safe_amount = round(
        safe_amount,
        2,
    )

    if (
        affordability_status
        not in VALID_STATUSES
    ):

        affordability_status = (
            "not_affordable"
        )

    if (
        recommended_payment_method
        not in VALID_PAYMENT_METHODS
    ):

        recommended_payment_method = (
            "not_recommended"
        )

    if not explanation.strip():

        explanation = (
            "No decision explanation available."
        )

    # =========================================================
    # 16. FINAL OUTPUT
    # =========================================================

    return {
        "request_id": request_id,

        "amount_safe_to_pay": safe_amount,

        "affordability_status":
            affordability_status,

        "recommended_payment_method":
            recommended_payment_method,

        "payment_plan":
            payment_plan,

        "earliest_date_for_full_payment":
            (
                pd.Timestamp(
                    earliest_full_payment_date
                ).strftime("%Y-%m-%d")
                if earliest_full_payment_date is not None
                else ""
            ),

        "spending_changes_needed":
            format_spending_changes(
                final_spending_changes
            ),

        "decision_explanation":
            explanation,
    }


# =============================================================
# DIRECT TEST
# =============================================================

if __name__ == "__main__":

    print("=" * 80)
    print("BUY OR WAIT - DECISION ENGINE TEST")
    print("=" * 80)

    data = load_data()

    request = data["requests"].iloc[0]

    result = analyze_request(
        request=request,
        data=data,
    )

    print("\nFINAL REQUEST ANALYSIS")
    print("-" * 80)

    for key, value in result.items():

        print(
            f"{key}: {value}"
        )

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)