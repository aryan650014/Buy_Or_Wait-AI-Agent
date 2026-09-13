import pandas as pd

from payment_schedule import generate_payment_schedule


def validate_installment_option(
    option,
    desired_completion_date,
    max_installment_months
):
    """
    Validate an installment option against:
    1. Payment method
    2. User's maximum installment duration
    3. Desired completion deadline
    """

    if option["payment_method"] != "installments":
        return {
            "eligible": False,
            "reason": "not_installment"
        }

    schedule = generate_payment_schedule(option)

    if not schedule:
        return {
            "eligible": False,
            "reason": "empty_schedule"
        }

    first_payment_date = schedule[0]["payment_date"]
    final_payment_date = schedule[-1]["payment_date"]

    # Deadline check
    if final_payment_date > desired_completion_date:
        return {
            "eligible": False,
            "reason": "misses_deadline",
            "final_payment_date": final_payment_date
        }

    # Maximum installment duration
    if pd.isna(max_installment_months):
        duration_ok = True
    else:
        allowed_end_date = (
            first_payment_date
            + pd.DateOffset(
                months=int(max_installment_months)
            )
        )

        duration_ok = final_payment_date <= allowed_end_date

    if not duration_ok:
        return {
            "eligible": False,
            "reason": "exceeds_max_installment_months",
            "final_payment_date": final_payment_date
        }

    return {
        "eligible": True,
        "reason": "valid",
        "first_payment_date": first_payment_date,
        "final_payment_date": final_payment_date,
        "number_of_payments": len(schedule),
        "payment_amount": option["payment_amount"],
        "total_payable_amount": option["total_payable_amount"]
    }


if __name__ == "__main__":

    from data_loader import load_data

    data = load_data()

    request_id = "request_26"

    request = data["requests"][
        data["requests"]["request_id"] == request_id
    ].iloc[0]

    profile = data["financial_profiles"][
        data["financial_profiles"]["user_id"]
        == request["user_id"]
    ].iloc[0]

    options = data["request_payment_options"][
        data["request_payment_options"]["request_id"]
        == request_id
    ]

    print("Installment Validation")
    print("=" * 75)

    for _, option in options.iterrows():

        result = validate_installment_option(
            option=option,
            desired_completion_date=
                request["desired_completion_date"],
            max_installment_months=
                profile["max_installment_months"]
        )

        print(
            option["payment_option_id"],
            "|",
            option["payment_method"],
            "|",
            result["eligible"],
            "|",
            result["reason"]
        )

        if result["eligible"]:
            print(
                "   First:",
                result["first_payment_date"].date()
            )
            print(
                "   Final:",
                result["final_payment_date"].date()
            )