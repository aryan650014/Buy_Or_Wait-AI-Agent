import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = BASE_DIR / "dataset"
OUTPUT_FILE = BASE_DIR / "output.csv"

REQUIRED_COLUMNS = [
    "request_id",
    "amount_safe_to_pay",
    "affordability_status",
    "recommended_payment_method",
    "payment_plan",
    "earliest_date_for_full_payment",
    "spending_changes_needed",
    "decision_explanation",
]

VALID_STATUSES = {
    "affordable_now",
    "affordable_with_plan",
    "affordable_later",
    "not_affordable",
}

VALID_METHODS = {
    "full_payment",
    "partial_payment",
    "installments",
    "wait",
    "not_recommended",
}


def main():
    print("=" * 80)
    print("BUY OR WAIT - FINAL OUTPUT VALIDATION")
    print("=" * 80)

    # Load files
    output = pd.read_csv(OUTPUT_FILE)
    requests = pd.read_csv(DATASET_DIR / "requests.csv")

    errors = []

    # ---------------------------------------------------------
    # 1. Row count
    # ---------------------------------------------------------
    if len(output) != len(requests):
        errors.append(
            f"Row count mismatch: output={len(output)}, requests={len(requests)}"
        )
    else:
        print(f"PASS: Row count = {len(output)}")

    # ---------------------------------------------------------
    # 2. Exact columns
    # ---------------------------------------------------------
    if list(output.columns) != REQUIRED_COLUMNS:
        errors.append(
            f"Column mismatch.\nExpected: {REQUIRED_COLUMNS}\n"
            f"Actual: {list(output.columns)}"
        )
    else:
        print("PASS: Exact 8 required columns")

    # ---------------------------------------------------------
    # 3. Request IDs
    # ---------------------------------------------------------
    expected_ids = set(requests["request_id"].astype(str))
    actual_ids = set(output["request_id"].astype(str))

    missing_ids = expected_ids - actual_ids
    extra_ids = actual_ids - expected_ids
    duplicate_ids = output["request_id"][
        output["request_id"].duplicated()
    ].tolist()

    if missing_ids:
        errors.append(f"Missing request IDs: {sorted(missing_ids)}")

    if extra_ids:
        errors.append(f"Extra request IDs: {sorted(extra_ids)}")

    if duplicate_ids:
        errors.append(f"Duplicate request IDs: {duplicate_ids}")

    if not missing_ids and not extra_ids and not duplicate_ids:
        print("PASS: Request IDs are complete and unique")

    # ---------------------------------------------------------
    # 4. Affordability status
    # ---------------------------------------------------------
    invalid_status = output[
        ~output["affordability_status"].isin(VALID_STATUSES)
    ]

    if not invalid_status.empty:
        errors.append(
            f"Invalid affordability statuses: "
            f"{invalid_status['affordability_status'].unique().tolist()}"
        )
    else:
        print("PASS: All affordability statuses are valid")

    # ---------------------------------------------------------
    # 5. Payment method
    # ---------------------------------------------------------
    invalid_methods = output[
        ~output["recommended_payment_method"].isin(VALID_METHODS)
    ]

    if not invalid_methods.empty:
        errors.append(
            f"Invalid payment methods: "
            f"{invalid_methods['recommended_payment_method'].unique().tolist()}"
        )
    else:
        print("PASS: All payment methods are valid")

    # ---------------------------------------------------------
    # 6. amount_safe_to_pay
    # ---------------------------------------------------------
    request_amounts = requests.set_index("request_id")["requested_amount"]

    amount_errors = []

    for _, row in output.iterrows():
        request_id = row["request_id"]
        safe_amount = row["amount_safe_to_pay"]

        if request_id not in request_amounts:
            continue

        requested_amount = float(request_amounts[request_id])

        if pd.isna(safe_amount):
            amount_errors.append(
                f"{request_id}: amount_safe_to_pay is blank"
            )
        elif float(safe_amount) < 0:
            amount_errors.append(
                f"{request_id}: safe amount is negative"
            )
        elif float(safe_amount) > requested_amount + 0.01:
            amount_errors.append(
                f"{request_id}: safe={safe_amount} > requested={requested_amount}"
            )

    if amount_errors:
        errors.extend(amount_errors)
    else:
        print("PASS: amount_safe_to_pay is within valid bounds")

    # ---------------------------------------------------------
    # 7. Required text fields
    # ---------------------------------------------------------
    for column in [
        "payment_plan",
        "spending_changes_needed",
        "decision_explanation",
    ]:
        bad = output[
            output[column].isna()
            | (output[column].astype(str).str.strip() == "")
        ]

        if not bad.empty:
            errors.append(
                f"{column} has blank values for: "
                f"{bad['request_id'].tolist()}"
            )

    print("PASS: Required text fields checked")

    # ---------------------------------------------------------
    # 8. Payment plan basic format
    # ---------------------------------------------------------
    plan_errors = []

    for _, row in output.iterrows():
        request_id = row["request_id"]
        method = row["recommended_payment_method"]
        plan = str(row["payment_plan"]).strip()

        if method == "not_recommended":
            if plan.lower() != "none":
                plan_errors.append(
                    f"{request_id}: not_recommended must have payment_plan=none"
                )

        elif method == "wait":
            if plan.lower() == "none":
                plan_errors.append(
                    f"{request_id}: wait must have a payment date"
                )

        else:
            if plan.lower() == "none":
                plan_errors.append(
                    f"{request_id}: {method} cannot have payment_plan=none"
                )

    if plan_errors:
        errors.extend(plan_errors)
    else:
        print("PASS: Payment plans have valid basic structure")

    # ---------------------------------------------------------
    # 9. Spending changes basic format
    # ---------------------------------------------------------
    spending_errors = []

    for _, row in output.iterrows():
        request_id = row["request_id"]
        changes = str(row["spending_changes_needed"]).strip()

        if changes.lower() == "none":
            continue

        parts = changes.split("|")

        if len(parts) > 3:
            spending_errors.append(
                f"{request_id}: more than 3 spending changes"
            )
            continue

        for change in parts:
            if change.startswith("stop:"):
                if len(change.split(":")) != 2:
                    spending_errors.append(
                        f"{request_id}: invalid stop format: {change}"
                    )

            elif change.startswith("reduce_to:"):
                pieces = change.split(":")
                if len(pieces) != 3:
                    spending_errors.append(
                        f"{request_id}: invalid reduce_to format: {change}"
                    )
                else:
                    try:
                        amount = float(pieces[2])
                        if amount < 0:
                            spending_errors.append(
                                f"{request_id}: negative reduce_to amount"
                            )
                    except ValueError:
                        spending_errors.append(
                            f"{request_id}: invalid reduce_to amount: {change}"
                        )

            else:
                spending_errors.append(
                    f"{request_id}: invalid spending change: {change}"
                )

    if spending_errors:
        errors.extend(spending_errors)
    else:
        print("PASS: Spending changes have valid basic format")

    # ---------------------------------------------------------
    # FINAL RESULT
    # ---------------------------------------------------------
    print()
    print("=" * 80)

    if errors:
        print("VALIDATION FAILED")
        print("=" * 80)
        print(f"Total problems: {len(errors)}")

        for i, error in enumerate(errors, 1):
            print(f"{i}. {error}")

        raise SystemExit(1)

    print("ALL VALIDATIONS PASSED")
    print("=" * 80)
    print()
    print("output.csv is structurally valid and ready for the deeper")
    print("payment-option / installment validation stage.")


if __name__ == "__main__":
    main()
    