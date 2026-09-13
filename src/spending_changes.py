from recurring_events import find_recurring_events


def parse_categories(value):
    """Convert pipe-separated category text into a lowercase set."""

    if not isinstance(value, str):
        return set()

    return {
        item.strip().lower()
        for item in value.split("|")
        if item.strip()
    }


def is_protected_category(category, protected_categories):
    protected = parse_categories(protected_categories)

    if not isinstance(category, str):
        return False

    return category.strip().lower() in protected


def is_flexible_expense(event):
    """Return True only for flexible debit expenses/subscriptions."""

    direction = str(event["direction"]).strip().lower()
    event_type = str(event["event_type"]).strip().lower()
    flexibility = str(event["flexibility"]).strip().lower()

    if direction != "debit":
        return False

    if event_type not in {"expense", "subscription"}:
        return False

    return flexibility in {
        "reducible",
        "stoppable",
        "reducible_or_stoppable",
    }


def get_changeable_recurring_expenses(
    events,
    protected_categories
):
    """
    Find recurring expenses that the user is allowed
    to reduce or stop.
    """

    recurring = find_recurring_events(events)

    candidates = []

    for _, recurring_event in recurring.iterrows():

        # Only recurring debits
        if str(
            recurring_event["direction"]
        ).strip().lower() != "debit":
            continue

        matching_events = events[
            (events["user_id"] == recurring_event["user_id"])
            & (
                events["description"]
                == recurring_event["description"]
            )
            & (
                events["category"]
                == recurring_event["category"]
            )
            & (
                events["direction"]
                == "debit"
            )
        ]

        if matching_events.empty:
            continue

        # Use latest occurrence to determine flexibility
        latest_event = (
            matching_events
            .sort_values("event_date")
            .iloc[-1]
        )

        # Must be an eligible expense/subscription
        if not is_flexible_expense(latest_event):
            continue

        # Protected categories cannot be changed
        if is_protected_category(
            recurring_event["category"],
            protected_categories
        ):
            continue

        average_amount = recurring_event[
            "average_amount"
        ]

        if average_amount is None:
            continue

        if isinstance(average_amount, float):
            if average_amount != average_amount:
                continue

        minimum_amount = latest_event[
            "minimum_allowed_amount"
        ]

        # Store useful information for the optimizer
        candidates.append({
            "event_id": latest_event["event_id"],
            "description": recurring_event["description"],
            "category": recurring_event["category"],
            "flexibility": latest_event["flexibility"],
            "average_amount": float(average_amount),
            "minimum_allowed_amount": minimum_amount,
            "occurrences": int(
                recurring_event["occurrences"]
            ),
            "frequency": recurring_event["frequency"],
        })

    return candidates


def calculate_potential_saving(candidate):
    """
    Estimate how much one spending change can save.
    """

    average_amount = candidate["average_amount"]
    flexibility = candidate["flexibility"]
    minimum_amount = candidate[
        "minimum_allowed_amount"
    ]

    # Stopping the expense saves the full recurring amount.
    if flexibility in {
        "stoppable",
        "reducible_or_stoppable",
    }:
        return average_amount

    # Reduction saves average - minimum.
    if flexibility == "reducible":

        if minimum_amount is None:
            return 0.0

        try:
            saving = (
                average_amount
                - float(minimum_amount)
            )

            return max(0.0, saving)

        except (TypeError, ValueError):
            return 0.0

    return 0.0


def build_change(candidate):
    """Create the required spending-change instruction."""

    event_id = candidate["event_id"]
    flexibility = candidate["flexibility"]
    minimum_amount = candidate[
        "minimum_allowed_amount"
    ]

    # Prefer stopping when allowed because it creates
    # the maximum possible saving.
    if flexibility in {
        "stoppable",
        "reducible_or_stoppable",
    }:
        return f"stop:{event_id}"

    if flexibility == "reducible":

        if minimum_amount is not None:
            return (
                f"reduce_to:{event_id}:"
                f"{float(minimum_amount):.2f}"
            )

    return None


def generate_spending_changes(
    events,
    protected_categories,
    max_changes=3
):
    """
    Generate the strongest eligible spending changes.

    Important:
    This function does NOT blindly modify protected/fixed
    expenses and does not create more than max_changes.
    """

    candidates = get_changeable_recurring_expenses(
        events=events,
        protected_categories=protected_categories
    )

    # Calculate estimated benefit of every candidate
    for candidate in candidates:
        candidate["potential_saving"] = (
            calculate_potential_saving(candidate)
        )

    # Remove changes that provide no financial benefit
    candidates = [
        candidate
        for candidate in candidates
        if candidate["potential_saving"] > 0
    ]

    # Highest potential saving first.
    candidates.sort(
        key=lambda x: (
            x["potential_saving"],
            x["average_amount"]
        ),
        reverse=True
    )

    changes = []

    for candidate in candidates:

        if len(changes) >= max_changes:
            break

        change = build_change(candidate)

        if change is not None:
            changes.append(change)

    return changes


if __name__ == "__main__":

    from data_loader import load_data
    from event_resolver import get_user_events

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

    changes = generate_spending_changes(
        events=events,
        protected_categories=profile[
            "expense_categories_to_protect"
        ],
        max_changes=3
    )

    print()
    print("SPENDING CHANGES")
    print("=" * 70)

    print("User:", user_id)

    print("\nSuggested Changes:")

    if changes:
        for change in changes:
            print(" ", change)
    else:
        print(" None")