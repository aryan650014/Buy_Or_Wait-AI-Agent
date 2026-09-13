import pandas as pd

from data_loader import load_data
from decision_engine import analyze_request


OUTPUT_COLUMNS = [
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


VALID_PAYMENT_METHODS = {
    "full_payment",
    "partial_payment",
    "installments",
    "wait",
    "not_recommended",
}


def validate_result(result, request):
    """
    Validate one generated result.
    """

    # Exact columns
    if list(result.keys()) != OUTPUT_COLUMNS:
        raise ValueError(
            f"Invalid columns for {request['request_id']}"
        )

    request_id = result["request_id"]

    if request_id != request["request_id"]:
        raise ValueError(
            f"Request ID mismatch: {request_id}"
        )

    # Requested amount
    requested_amount = float(
        request["requested_amount"]
    )

    # Safe amount
    safe_amount = float(
        result["amount_safe_to_pay"]
    )

    if safe_amount < 0:
        raise ValueError(
            f"Negative safe amount: {request_id}"
        )

    if safe_amount > requested_amount + 0.01:
        raise ValueError(
            f"Safe amount exceeds requested amount: {request_id}"
        )

    # Status
    if result["affordability_status"] not in VALID_STATUSES:
        raise ValueError(
            f"Invalid affordability status: {request_id}"
        )

    # Payment method
    if (
        result["recommended_payment_method"]
        not in VALID_PAYMENT_METHODS
    ):
        raise ValueError(
            f"Invalid payment method: {request_id}"
        )

    # Explanation
    explanation = str(
        result["decision_explanation"]
    ).strip()

    if not explanation:
        raise ValueError(
            f"Missing explanation: {request_id}"
        )

    return True


def generate_output():
    print("=" * 80)
    print("BUY OR WAIT - GENERATING OUTPUT")
    print("=" * 80)

    data = load_data()

    requests = data["requests"]

    print(
        f"\nTotal requests: {len(requests)}"
    )

    results = []
    errors = []

    # ========================================================
    # PROCESS ALL REQUESTS
    # ========================================================

    for index, (_, request) in enumerate(
        requests.iterrows(),
        start=1,
    ):

        request_id = request["request_id"]

        print(
            f"[{index}/{len(requests)}] "
            f"Processing {request_id}..."
        )

        try:

            result = analyze_request(
                request=request,
                data=data,
            )

            validate_result(
                result=result,
                request=request,
            )

            results.append(result)

        except Exception as error:
            import traceback

            print("\n" + "=" * 80)
            print(f"FAILED REQUEST: {request_id}")
            print("=" * 80)
            traceback.print_exc()
            print("=" * 80)

            errors.append(
                {
                    "request_id": request_id,
                    "error": str(error),
                }
            )

    # ========================================================
    # ERROR CHECK
    # ========================================================

    print("\n" + "=" * 80)
    print("PROCESSING SUMMARY")
    print("=" * 80)

    print(
        f"Successfully processed: "
        f"{len(results)}"
    )

    print(
        f"Errors: {len(errors)}"
    )

    if errors:

        print("\nERROR DETAILS:")

        for error in errors[:20]:

            print(
                f"- {error['request_id']}: "
                f"{error['error']}"
            )

        raise RuntimeError(
            f"{len(errors)} requests failed. "
            f"Output was NOT generated."
        )

    # ========================================================
    # CREATE DATAFRAME
    # ========================================================

    output_df = pd.DataFrame(
        results,
        columns=OUTPUT_COLUMNS,
    )

    # ========================================================
    # FINAL VALIDATION
    # ========================================================

    if len(output_df) != len(requests):

        raise ValueError(
            f"Expected {len(requests)} rows, "
            f"got {len(output_df)}"
        )

    # Duplicate IDs
    if output_df[
        "request_id"
    ].duplicated().any():

        raise ValueError(
            "Duplicate request_id found."
        )

    # Missing IDs
    expected_ids = set(
        requests["request_id"]
    )

    actual_ids = set(
        output_df["request_id"]
    )

    missing_ids = (
        expected_ids - actual_ids
    )

    extra_ids = (
        actual_ids - expected_ids
    )

    if missing_ids:

        raise ValueError(
            f"Missing request IDs: "
            f"{sorted(missing_ids)}"
        )

    if extra_ids:

        raise ValueError(
            f"Unexpected request IDs: "
            f"{sorted(extra_ids)}"
        )

    # Exact column order
    if list(
        output_df.columns
    ) != OUTPUT_COLUMNS:

        raise ValueError(
            "Output columns are incorrect."
        )

    # Safe amount bounds
    merged = output_df.merge(
        requests[
            [
                "request_id",
                "requested_amount",
            ]
        ],
        on="request_id",
        how="left",
    )

    if (
        merged["amount_safe_to_pay"] < 0
    ).any():

        raise ValueError(
            "Some safe amounts are negative."
        )

    if (
        merged["amount_safe_to_pay"]
        > merged["requested_amount"] + 0.01
    ).any():

        raise ValueError(
            "Some safe amounts exceed requested amount."
        )

    # ========================================================
    # SAVE
    # ========================================================

    output_path = (
        pd.Path("output.csv")
        if hasattr(pd, "Path")
        else "output.csv"
    )

    output_df.to_csv(
        "output.csv",
        index=False,
    )

    # ========================================================
    # DISTRIBUTIONS
    # ========================================================

    print("\nAffordability distribution:")

    print(
        output_df[
            "affordability_status"
        ].value_counts()
    )

    print(
        "\nPayment method distribution:"
    )

    print(
        output_df[
            "recommended_payment_method"
        ].value_counts()
    )

    # ========================================================
    # SAMPLE
    # ========================================================

    print(
        "\nFirst 10 output rows:"
    )

    print(
        output_df.head(10).to_string(
            index=False
        )
    )

    print("\n" + "=" * 80)
    print("OUTPUT GENERATED SUCCESSFULLY")
    print("=" * 80)

    print(
        "\nFile: output.csv"
    )

    print(
        f"Rows: {len(output_df)}"
    )

    print(
        f"Columns: {len(output_df.columns)}"
    )


if __name__ == "__main__":
    generate_output()