def rank_candidate_plans(candidates):
    """
    Rank eligible payment plans according to hackathon rules.

    Ranking priority:
    1. Complete by deadline
    2. No spending changes
    3. Lowest total payable amount
    4. Earlier start date
    5. Fewer payments
    6. Lowest payment_option_id
    """

    if not candidates:
        return []

    ranked = sorted(
        candidates,
        key=lambda plan: (
            not plan.get("completes_by_deadline", True),
            plan.get("spending_changes_count", 0),
            plan["total_payable_amount"],
            plan["first_payment_date"],
            plan["number_of_payments"],
            plan["payment_option_id"],
        )
    )

    return ranked


def select_best_plan(candidates):
    ranked = rank_candidate_plans(candidates)

    if not ranked:
        return None

    return ranked[0]


if __name__ == "__main__":

    candidates = [
        {
            "payment_option_id": "payment_option_74",
            "payment_method": "installments",
            "payment_amount": 2818080.00,
            "number_of_payments": 6,
            "first_payment_date": "2025-08-10",
            "final_payment_date": "2025-10-07",
            "total_payable_amount": 16908480.00,
            "completes_by_deadline": True,
            "spending_changes_count": 0
        },
        {
            "payment_option_id": "payment_option_72",
            "payment_method": "full_payment",
            "payment_amount": 15656000.00,
            "number_of_payments": 1,
            "first_payment_date": "2025-08-03",
            "final_payment_date": "2025-08-03",
            "total_payable_amount": 15656000.00,
            "completes_by_deadline": True,
            "spending_changes_count": 0
        }
    ]

    ranked = rank_candidate_plans(candidates)

    print("Plan Ranking")
    print("=" * 70)

    for i, plan in enumerate(ranked, start=1):
        print(
            f"{i}. {plan['payment_option_id']} | "
            f"{plan['payment_method']} | "
            f"Total: {plan['total_payable_amount']:,.2f}"
        )

    best = select_best_plan(candidates)

    print("\nBest Plan:")
    print(best["payment_option_id"])