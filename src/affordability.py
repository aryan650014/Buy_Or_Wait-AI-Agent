def determine_affordability_status(
    requested_amount,
    amount_safe_to_pay,
    best_plan=None,
    earliest_full_payment_date=None,
    desired_completion_date=None,
):
    """
    Determine the final affordability status.

    Possible statuses:
        affordable_now
        affordable_with_plan
        affordable_later
        not_affordable
    """

    # Full requested amount is safe today.
    if amount_safe_to_pay >= requested_amount:
        if best_plan is not None:
            if best_plan.get("payment_method") != "full_payment":
                return "affordable_with_plan"

        return "affordable_now"

    # A valid payment plan can complete the purchase
    # within the requested deadline.
    if best_plan is not None:
        return "affordable_with_plan"

    # Purchase can be fully paid later within deadline.
    if (
        earliest_full_payment_date is not None
        and desired_completion_date is not None
        and earliest_full_payment_date <= desired_completion_date
    ):
        return "affordable_later"

    # No safe way to complete the purchase.
    return "not_affordable"


if __name__ == "__main__":

    print("Affordability Tests")
    print("=" * 60)

    print(
        "Test 1:",
        determine_affordability_status(
            requested_amount=10000,
            amount_safe_to_pay=10000
        )
    )

    print(
        "Test 2:",
        determine_affordability_status(
            requested_amount=10000,
            amount_safe_to_pay=5000,
            best_plan={
                "payment_method": "installments"
            }
        )
    )

    print(
        "Test 3:",
        determine_affordability_status(
            requested_amount=10000,
            amount_safe_to_pay=5000,
            earliest_full_payment_date="2025-09-15",
            desired_completion_date="2025-10-01"
        )
    )

    print(
        "Test 4:",
        determine_affordability_status(
            requested_amount=10000,
            amount_safe_to_pay=0
        )
    )