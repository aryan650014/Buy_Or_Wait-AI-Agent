def is_partial_payment_eligible(
    allows_partial_payment,
    payment_preferences,
    amount_safe_to_pay,
    requested_amount,
    earliest_full_payment_date,
    desired_completion_date
):
    """
    Check whether partial payment is allowed under hackathon rules.
    """

    if not allows_partial_payment:
        return False

    if "partial_payment" not in payment_preferences:
        return False

    if amount_safe_to_pay <= 0:
        return False

    if amount_safe_to_pay >= requested_amount:
        return False

    if earliest_full_payment_date is None:
        return False

    if earliest_full_payment_date > desired_completion_date:
        return False

    return True


def create_partial_payment_plan(
    amount_safe_to_pay,
    requested_amount,
    request_date,
    earliest_full_payment_date
):
    """
    Create exactly two payments.
    """

    remaining_amount = round(
        requested_amount - amount_safe_to_pay,
        2
    )

    return {
        "payment_method": "partial_payment",
        "payments": [
            {
                "payment_number": 1,
                "payment_date": request_date,
                "amount": round(amount_safe_to_pay, 2)
            },
            {
                "payment_number": 2,
                "payment_date": earliest_full_payment_date,
                "amount": remaining_amount
            }
        ]
    }


if __name__ == "__main__":

    # Sample test similar to request_19
    requested_amount = 39660.00
    amount_safe = 28820.00

    eligible = is_partial_payment_eligible(
        allows_partial_payment=True,
        payment_preferences=[
            "full_payment",
            "partial_payment"
        ],
        amount_safe_to_pay=amount_safe,
        requested_amount=requested_amount,
        earliest_full_payment_date="2025-09-15",
        desired_completion_date="2025-09-30"
    )

    print("Partial Payment Test")
    print("=" * 60)

    print("Eligible:", eligible)

    if eligible:

        plan = create_partial_payment_plan(
            amount_safe_to_pay=amount_safe,
            requested_amount=requested_amount,
            request_date="2025-08-03",
            earliest_full_payment_date="2025-09-15"
        )

        print("\nPayment Plan:")

        for payment in plan["payments"]:
            print(
                f"Payment {payment['payment_number']} | "
                f"{payment['payment_date']} | "
                f"{payment['amount']:,.2f}"
            )