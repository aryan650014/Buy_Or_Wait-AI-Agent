from data_loader import load_data


# ============================================================
# EVENT STATUS RULES
# ============================================================

IGNORED_STATUSES = {
    "failed",
    "cancelled",
    "unrealized",
}


# ============================================================
# CHECK WHETHER EVENT IS VALID
# ============================================================

def is_valid_event(event):
    """
    Apply the hackathon event-status rules.

    Rules:
    - Failed transactions are ignored.
    - Cancelled transactions are ignored.
    - Unrealized investment valuations are ignored.
    - Pending credits are ignored.
    - Pending debits are retained.
    - Settled transactions are retained.
    - Scheduled transactions are retained.
    """

    status = str(event["status"]).strip().lower()
    direction = str(event["direction"]).strip().lower()

    # Always ignore these statuses.
    if status in IGNORED_STATUSES:
        return False

    # Pending credits must NOT be treated as available money.
    if status == "pending" and direction == "credit":
        return False

    # Pending debit can still represent an upcoming obligation.
    if status == "pending" and direction == "debit":
        return True

    # Settled and scheduled events are valid.
    if status in {"settled", "scheduled"}:
        return True

    # Unknown statuses are ignored for safety.
    return False


# ============================================================
# GET VALID EVENTS
# ============================================================

def get_valid_events(events):
    """
    Return events that are valid for financial calculations.
    """

    mask = events.apply(
        is_valid_event,
        axis=1
    )

    return events[mask].copy()


# ============================================================
# GET USER EVENTS
# ============================================================

def get_user_events(events, user_id):
    """
    Return valid events belonging to a specific user.
    """

    valid_events = get_valid_events(events)

    user_events = valid_events[
        valid_events["user_id"] == user_id
    ].copy()

    return user_events


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    data = load_data()

    events = data["financial_events"]

    valid_events = get_valid_events(events)

    print()
    print("EVENT RESOLVER TEST")
    print("=" * 70)

    print(
        "Total events:",
        len(events)
    )

    print(
        "Valid events:",
        len(valid_events)
    )

    print(
        "Ignored events:",
        len(events) - len(valid_events)
    )

    print()
    print("Original status distribution:")
    print(
        events["status"].value_counts()
    )

    print()
    print("Valid status distribution:")
    print(
        valid_events["status"].value_counts()
    )

    print()

    # Check pending events specifically.
    pending_events = events[
        events["status"].str.lower() == "pending"
    ]

    valid_pending_events = valid_events[
        valid_events["status"].str.lower() == "pending"
    ]

    print(
        "Total pending events:",
        len(pending_events)
    )

    print(
        "Valid pending events:",
        len(valid_pending_events)
    )

    if not valid_pending_events.empty:

        print()
        print("Valid pending events:")
        print(
            valid_pending_events[
                [
                    "event_id",
                    "user_id",
                    "event_type",
                    "description",
                    "amount",
                    "currency",
                    "direction",
                    "event_date",
                    "status",
                ]
            ].to_string(index=False)
        )