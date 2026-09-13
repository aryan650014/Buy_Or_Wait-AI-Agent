import pandas as pd
from pathlib import Path
import re

BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = BASE_DIR / "dataset"
OUTPUT_FILE = BASE_DIR / "output.csv"

VALID_METHODS = {
    "full_payment",
    "partial_payment",
    "installments",
    "wait",
    "not_recommended",
}


def parse_payment_plan(plan):
    """
    Convert:
        2025-08-03:1000|2025-08-10:2000

    into:
        [(Timestamp, 1000.0), (Timestamp, 2000.0)]
    """

    plan = str(plan).strip()

    if plan.lower() == "none":
        return []

    payments = []

    for item in plan.split("|"):
        item = item.strip()

        match = re.fullmatch(
            r"(\d{4}-\d{2}-\d{2}):([0-9]+(?:\.[0-9]+)?)",
            item,
        )

        if not match:
            raise ValueError(
                f"Invalid payment entry: {item}"
            )

        date = pd.Timestamp(match.group(1))
        amount = float(match.group(2))

        payments.append((date, amount))

    return payments


def get_payment_options(payment_options, request_id):
    return payment_options[
        payment_options["request_id"] == request_id
    ].copy()


def option_matches_schedule(option, payments):
    """
    Check whether output payment plan exactly matches
    the supplied payment option.
    """

    number_of_payments = int(option["number_of_payments"])

    if len(payments) != number_of_payments:
        return False

    first_date = pd.Timestamp(
        option["first_payment_date"]
    ).normalize()

    frequency = option["payment_frequency_days"]

    payment_amount = float(option["payment_amount"])

    for i, (date, amount) in enumerate(payments):

        if pd.Timestamp(date).normalize() != (
            first_date
            if pd.isna(frequency)
            else first_date
            + pd.Timedelta(
                days=int(frequency) * i
            )
        ):
            return False

        if abs(amount - payment_amount) > 0.02:
            return False

    return True


def months_between(start, end):
    return (
        (end.year - start.year) * 12
        + (end.month - start.month)
    )


def main():

    print("=" * 80)
    print("BUY OR WAIT - DEEP PAYMENT RULE VALIDATION")
    print("=" * 80)

    output = pd.read_csv(OUTPUT_FILE)

    requests = pd.read_csv(
        DATASET_DIR / "requests.csv"
    )

    payment_options = pd.read_csv(
        DATASET_DIR / "request_payment_options.csv"
    )

    profiles = pd.read_csv(
        DATASET_DIR / "financial_profiles.csv"
    )

    requests["request_date"] = pd.to_datetime(
        requests["request_date"]
    )

    requests["desired_completion_date"] = pd.to_datetime(
        requests["desired_completion_date"]
    )

    payment_options["first_payment_date"] = pd.to_datetime(
        payment_options["first_payment_date"]
    )

    errors = []

    request_lookup = requests.set_index(
        "request_id"
    )

    profile_lookup = profiles.set_index(
        "user_id"
    )

    # =========================================================
    # Check every output row
    # =========================================================

    for _, row in output.iterrows():

        request_id = row["request_id"]
        method = str(
            row["recommended_payment_method"]
        ).strip()

        plan = str(
            row["payment_plan"]
        ).strip()

        request = request_lookup.loc[request_id]

        request_date = pd.Timestamp(
            request["request_date"]
        ).normalize()

        deadline = pd.Timestamp(
            request["desired_completion_date"]
        ).normalize()

        requested_amount = float(
            request["requested_amount"]
        )

        user_id = request["user_id"]

        profile = profile_lookup.loc[user_id]

        max_installment_months = float(
            profile["max_installment_months"]
        )

        try:
            payments = parse_payment_plan(plan)
        except Exception as exc:
            errors.append(
                f"{request_id}: {exc}"
            )
            continue

        # =====================================================
        # NOT RECOMMENDED
        # =====================================================

        if method == "not_recommended":

            if payments:
                errors.append(
                    f"{request_id}: "
                    f"not_recommended must have payment_plan=none"
                )

            continue

        # =====================================================
        # WAIT
        # =====================================================

        if method == "wait":

            if len(payments) != 1:
                errors.append(
                    f"{request_id}: "
                    f"wait must contain exactly one payment"
                )
                continue

            payment_date, payment_amount = payments[0]

            if payment_date <= request_date:
                errors.append(
                    f"{request_id}: "
                    f"wait payment must be after request date"
                )

            if payment_date > deadline:
                errors.append(
                    f"{request_id}: "
                    f"wait payment occurs after desired deadline"
                )

            earliest = row[
                "earliest_date_for_full_payment"
            ]

            if str(earliest).strip().lower() != "none":
                earliest_date = pd.Timestamp(
                    earliest
                ).normalize()

                if earliest_date != payment_date:
                    errors.append(
                        f"{request_id}: "
                        f"earliest payment date does not match wait plan"
                    )

            continue

        # =====================================================
        # FULL PAYMENT
        # =====================================================

        if method == "full_payment":

            if len(payments) != 1:
                errors.append(
                    f"{request_id}: "
                    f"full_payment must contain exactly one payment"
                )
                continue

            payment_date, payment_amount = payments[0]

            if abs(
                payment_amount - requested_amount
            ) > 0.02:
                errors.append(
                    f"{request_id}: "
                    f"full payment amount "
                    f"{payment_amount} != "
                    f"requested amount {requested_amount}"
                )

            if payment_date > deadline:
                errors.append(
                    f"{request_id}: "
                    f"full payment is after desired deadline"
                )

            continue

        # =====================================================
        # INSTALLMENTS
        # =====================================================

        if method == "installments":

            if len(payments) < 2:
                errors.append(
                    f"{request_id}: "
                    f"installments must have at least 2 payments"
                )
                continue

            options = get_payment_options(
                payment_options,
                request_id,
            )

            matched_option = False

            for _, option in options.iterrows():

                option_months = float(
                    option["number_of_payments"]
                )

                frequency = option[
                    "payment_frequency_days"
                ]

                first_date = pd.Timestamp(
                    option["first_payment_date"]
                ).normalize()

                if first_date < request_date:
                    continue

                last_date = first_date

                if not pd.isna(frequency):
                    last_date = (
                        first_date
                        + pd.Timedelta(
                            days=int(frequency)
                            * (
                                int(option_months) - 1
                            )
                        )
                    )

                if months_between(
                    first_date,
                    last_date
                ) > max_installment_months:
                    continue

                if last_date > deadline:
                    continue

                if option_matches_schedule(
                    option,
                    payments,
                ):
                    matched_option = True
                    break

            if not matched_option:
                errors.append(
                    f"{request_id}: "
                    f"installment plan does not exactly "
                    f"match any valid supplied payment option"
                )

            continue

        # =====================================================
        # PARTIAL PAYMENT
        # =====================================================

        if method == "partial_payment":

            if len(payments) != 2:
                errors.append(
                    f"{request_id}: "
                    f"partial_payment must contain exactly 2 payments"
                )
                continue

            first_date, first_amount = payments[0]
            second_date, second_amount = payments[1]

            # First payment must be today/request date
            if first_date != request_date:
                errors.append(
                    f"{request_id}: "
                    f"first partial payment must be on request date"
                )

            # Second payment must be later
            if second_date <= first_date:
                errors.append(
                    f"{request_id}: "
                    f"second partial payment must be after first"
                )

            # Total must equal requested amount
            total = first_amount + second_amount

            if abs(
                total - requested_amount
            ) > 0.02:
                errors.append(
                    f"{request_id}: "
                    f"partial payments total "
                    f"{total} != requested amount "
                    f"{requested_amount}"
                )

            # Second payment must be within deadline
            if second_date > deadline:
                errors.append(
                    f"{request_id}: "
                    f"remaining partial payment is after deadline"
                )

            # First payment must actually be partial
            if not (
                0 < first_amount < requested_amount
            ):
                errors.append(
                    f"{request_id}: "
                    f"first partial payment is not a valid partial amount"
                )

            continue

    # =========================================================
    # FINAL RESULT
    # =========================================================

    print()

    if errors:

        print("=" * 80)
        print("DEEP PAYMENT VALIDATION FAILED")
        print("=" * 80)

        print(
            f"Total payment-rule problems: {len(errors)}"
        )

        for i, error in enumerate(errors, 1):
            print(
                f"{i}. {error}"
            )

        raise SystemExit(1)

    print("=" * 80)
    print("ALL DEEP PAYMENT RULES PASSED")
    print("=" * 80)

    print()
    print("Checked:")
    print("  PASS - Full payment plans")
    print("  PASS - Wait plans")
    print("  PASS - Installment schedules")
    print("  PASS - Installment payment amounts")
    print("  PASS - Installment deadlines")
    print("  PASS - Maximum installment months")
    print("  PASS - Partial payment structure")
    print("  PASS - Partial payment totals")
    print("  PASS - Payment dates")
    print()
    print("output.csv passed the deep payment validation.")


if __name__ == "__main__":
    main()