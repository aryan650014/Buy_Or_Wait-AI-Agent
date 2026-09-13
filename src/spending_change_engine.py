import copy
import math


def apply_spending_changes(
    forecast_events,
    spending_changes
):
    """
    Apply spending changes to a COPY of forecast events.

    Supported formats:
        stop:event_id
        reduce_to:event_id:new_amount

    Original forecast_events are never modified.
    """

    updated_events = copy.deepcopy(
        forecast_events
    )

    if not spending_changes:
        return updated_events

    for change in spending_changes:

        if not isinstance(change, str):
            continue

        change = change.strip()

        if not change:
            continue

        parts = change.split(":")

        # --------------------------------------------------
        # STOP
        # --------------------------------------------------

        if len(parts) == 2 and parts[0] == "stop":

            event_id = parts[1].strip()

            if not event_id:
                continue

            for event in updated_events:

                if event.get("event_id") != event_id:
                    continue

                # Only debit events can be stopped
                if event.get("direction") != "debit":
                    continue

                # Do not create negative amounts
                event["amount"] = 0.0

        # --------------------------------------------------
        # REDUCE TO
        # --------------------------------------------------

        elif (
            len(parts) == 3
            and parts[0] == "reduce_to"
        ):

            event_id = parts[1].strip()

            try:
                new_amount = float(
                    parts[2]
                )
            except (TypeError, ValueError):
                continue

            # Invalid amount
            if not math.isfinite(new_amount):
                continue

            if new_amount < 0:
                continue

            for event in updated_events:

                if event.get("event_id") != event_id:
                    continue

                # Only debit events can be reduced
                if event.get("direction") != "debit":
                    continue

                current_amount = event.get(
                    "amount"
                )

                if current_amount is None:
                    continue

                try:
                    current_amount = float(
                        current_amount
                    )
                except (TypeError, ValueError):
                    continue

                # Reduction must actually reduce
                if new_amount < current_amount:
                    event["amount"] = new_amount

    return updated_events


def compare_forecasts(
    original_events,
    updated_events
):
    """
    Compare original and modified forecasts.

    Returns total debit saving and number of
    changed forecast events.
    """

    original_total = 0.0
    updated_total = 0.0
    changed_events = 0

    original_by_key = {
        (
            event.get("event_id"),
            str(event.get("event_date"))
        ): event
        for event in original_events
    }

    updated_by_key = {
        (
            event.get("event_id"),
            str(event.get("event_date"))
        ): event
        for event in updated_events
    }

    for key, original in original_by_key.items():

        updated = updated_by_key.get(key)

        if updated is None:
            continue

        if original.get("direction") != "debit":
            continue

        original_amount = original.get(
            "amount"
        )

        updated_amount = updated.get(
            "amount"
        )

        if original_amount is None:
            continue

        if updated_amount is None:
            continue

        original_amount = float(
            original_amount
        )

        updated_amount = float(
            updated_amount
        )

        original_total += original_amount
        updated_total += updated_amount

        if updated_amount != original_amount:
            changed_events += 1

    return {
        "original_debit_total": original_total,
        "updated_debit_total": updated_total,
        "total_saving": max(
            0.0,
            original_total - updated_total
        ),
        "changed_events": changed_events,
    }


if __name__ == "__main__":

    from data_loader import load_data
    from event_resolver import get_user_events
    from forecast import generate_forecast
    from spending_changes import (
        generate_spending_changes
    )

    data = load_data()

    request = data["requests"].iloc[0]

    user_id = request["user_id"]

    profile = data["financial_profiles"][
        data["financial_profiles"]["user_id"]
        == user_id
    ].iloc[0]

    events = get_user_events(
        data["financial_events"],
        user_id
    )

    forecast_events = generate_forecast(
        events=events,
        request_date=request["request_date"],
        days=90
    )

    spending_changes = (
        generate_spending_changes(
            events=events,
            protected_categories=profile[
                "expense_categories_to_protect"
            ],
            max_changes=3
        )
    )

    updated_events = apply_spending_changes(
        forecast_events=forecast_events,
        spending_changes=spending_changes
    )

    comparison = compare_forecasts(
        original_events=forecast_events,
        updated_events=updated_events
    )

    print()
    print("SPENDING CHANGE ENGINE TEST")
    print("=" * 70)

    print("User:", user_id)

    print(
        "Original forecast events:",
        len(forecast_events)
    )

    print(
        "Updated forecast events:",
        len(updated_events)
    )

    print(
        "Spending changes:",
        spending_changes
    )

    print()
    print(
        "Original debit total:",
        round(
            comparison[
                "original_debit_total"
            ],
            2
        )
    )

    print(
        "Updated debit total:",
        round(
            comparison[
                "updated_debit_total"
            ],
            2
        )
    )

    print(
        "Estimated saving:",
        round(
            comparison[
                "total_saving"
            ],
            2
        )
    )

    print(
        "Changed forecast events:",
        comparison[
            "changed_events"
        ]
    )