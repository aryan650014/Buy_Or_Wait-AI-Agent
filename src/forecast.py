from datetime import timedelta
import pandas as pd
from recurring_events import find_recurring_events


def generate_future_date(last_date, frequency):
    """
    Generate the next expected date for a recurring event.
    """

    if frequency == "monthly":
        return last_date + pd.DateOffset(months=1)

    if frequency == "weekly":
        return last_date + timedelta(days=7)

    if frequency == "quarterly":
        return last_date + pd.DateOffset(months=3)

    return None


def build_forecast_event(event, event_date, amount=None):
    """
    Create a standardized forecast event while preserving
    the original event_id and important event properties.
    """

    if amount is None:
        amount = event["amount"]

    return {
        "event_id": event["event_id"],
        "user_id": event["user_id"],
        "description": event["description"],
        "category": event["category"],
        "direction": event["direction"],
        "event_type": event["event_type"],
        "event_date": event_date,
        "amount": amount,
        "currency": event["currency"],
        "flexibility": event["flexibility"],
        "minimum_allowed_amount": event["minimum_allowed_amount"],
    }


def add_scheduled_events(
    events,
    request_date,
    forecast_end,
    forecast_events
):
    """
    Add valid scheduled events that fall inside the
    90-day forecast window.

    Scheduled events are already retained by event_resolver.py.
    Here we include them directly instead of trying to
    predict them through recurring-event detection.
    """

    scheduled_events = events[
        (events["status"].str.lower() == "scheduled")
        & (events["event_date"] > request_date)
        & (events["event_date"] <= forecast_end)
    ].copy()

    for _, event in scheduled_events.iterrows():

        # Do not add events with missing amounts here.
        # Blank amounts will be handled later by the
        # evidence/image resolver.
        if pd.isna(event["amount"]):
            continue

        forecast_events.append(
            build_forecast_event(
                event=event,
                event_date=event["event_date"],
                amount=event["amount"]
            )
        )

    return forecast_events


def add_recurring_events(
    events,
    request_date,
    forecast_end,
    forecast_events
):
    """
    Generate future occurrences of recurring events.

    Irregular events are intentionally skipped because
    their future occurrence cannot be reliably predicted
    from frequency alone.
    """

    recurring = find_recurring_events(events)

    for _, recurring_event in recurring.iterrows():

        frequency = recurring_event["frequency"]

        if frequency == "irregular":
            continue

        next_date = generate_future_date(
            recurring_event["last_date"],
            frequency
        )

        while (
            next_date is not None
            and next_date <= forecast_end
        ):

            if next_date > request_date:

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
                        == recurring_event["direction"]
                    )
                ].sort_values("event_date")

                if matching_events.empty:
                    break

                latest_event = matching_events.iloc[-1]

                # If the latest recurring event has no amount,
                # don't treat blank as zero.
                if pd.isna(recurring_event["average_amount"]):
                    next_date = generate_future_date(
                        next_date,
                        frequency
                    )
                    continue

                forecast_events.append(
                    build_forecast_event(
                        event=latest_event,
                        event_date=next_date,
                        amount=recurring_event["average_amount"]
                    )
                )

            next_date = generate_future_date(
                next_date,
                frequency
            )

    return forecast_events


def remove_duplicate_forecast_events(forecast_events):
    """
    Remove accidental duplicate forecast records.

    A scheduled event should not be duplicated if the same
    event is also detected by recurring-event logic.
    """

    unique_events = {}

    for event in forecast_events:

        key = (
            event["event_id"],
            pd.Timestamp(event["event_date"]).normalize()
        )

        unique_events[key] = event

    return list(unique_events.values())


def generate_forecast(events, request_date, days=90):
    """
    Generate the future financial forecast for the next N days.

    Includes:
    1. Direct scheduled events.
    2. Predictable recurring events.
    3. Original event_id and flexibility.
    4. Only events after request_date.
    5. Only events within the forecast window.

    Important:
    - Scheduled events are included directly.
    - Irregular events are not artificially predicted.
    - Blank amounts are NOT treated as zero.
    - Spending changes can later use event_id to modify
      recurring forecast events.
    """

    request_date = pd.Timestamp(request_date).normalize()

    forecast_end = (
        request_date + timedelta(days=days)
    )

    forecast_events = []

    # --------------------------------------------------
    # STEP 1: Add scheduled events
    # --------------------------------------------------

    forecast_events = add_scheduled_events(
        events=events,
        request_date=request_date,
        forecast_end=forecast_end,
        forecast_events=forecast_events
    )

    # --------------------------------------------------
    # STEP 2: Add predictable recurring events
    # --------------------------------------------------

    forecast_events = add_recurring_events(
        events=events,
        request_date=request_date,
        forecast_end=forecast_end,
        forecast_events=forecast_events
    )

    # --------------------------------------------------
    # STEP 3: Remove accidental duplicates
    # --------------------------------------------------

    forecast_events = remove_duplicate_forecast_events(
        forecast_events
    )

    # --------------------------------------------------
    # STEP 4: Sort chronologically
    # --------------------------------------------------

    forecast_events.sort(
        key=lambda x: x["event_date"]
    )

    return forecast_events


if __name__ == "__main__":

    from data_loader import load_data
    from event_resolver import get_user_events

    data = load_data()

    user_id = "user_26"
    request_date = pd.Timestamp("2025-08-03")

    user_events = get_user_events(
        data["financial_events"],
        user_id
    )

    forecast_events = generate_forecast(
        events=user_events,
        request_date=request_date,
        days=90
    )

    print()
    print("90-DAY FORECAST TEST")
    print("=" * 70)

    print("User:", user_id)
    print("Request date:", request_date.date())
    print("Forecast events:", len(forecast_events))
    print()

    if forecast_events:

        forecast_df = pd.DataFrame(forecast_events)

        print(
            forecast_df[
                [
                    "event_id",
                    "event_type",
                    "description",
                    "category",
                    "direction",
                    "amount",
                    "currency",
                    "event_date",
                    "flexibility",
                ]
            ].to_string(index=False)
        )

    else:
        print("No forecast events found.")