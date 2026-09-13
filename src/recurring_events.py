from data_loader import load_data
from event_resolver import get_user_events


def detect_frequency(dates):
    """
    Detect approximate frequency from event dates.
    """

    if len(dates) < 2:
        return "unknown"

    dates = sorted(dates)

    gaps = []

    for i in range(1, len(dates)):
        gap = (dates[i] - dates[i - 1]).days
        gaps.append(gap)

    average_gap = sum(gaps) / len(gaps)

    if 25 <= average_gap <= 35:
        return "monthly"

    if 6 <= average_gap <= 8:
        return "weekly"

    if 80 <= average_gap <= 100:
        return "quarterly"

    return "irregular"


def find_recurring_events(events):

    grouped = (
        events
        .groupby(
            [
                "user_id",
                "description",
                "category",
                "direction"
            ],
            dropna=False
        )
        .agg(
            occurrences=("event_id", "count"),
            first_date=("event_date", "min"),
            last_date=("event_date", "max"),
            average_amount=("amount", "mean"),
            minimum_amount=("amount", "min"),
            maximum_amount=("amount", "max"),
            dates=("event_date", list),
        )
        .reset_index()
    )

    recurring = grouped[
        grouped["occurrences"] >= 3
    ].copy()

    recurring["frequency"] = recurring["dates"].apply(
        detect_frequency
    )

    return recurring


if __name__ == "__main__":

    data = load_data()

    events = get_user_events(
        data["financial_events"],
        "user_26"
    )

    recurring = find_recurring_events(events)

    print("Recurring events for user_26")
    print("=" * 80)

    print(
        recurring[
            [
                "description",
                "category",
                "direction",
                "occurrences",
                "first_date",
                "last_date",
                "frequency",
                "average_amount",
                "minimum_amount",
                "maximum_amount",
            ]
        ]
        .sort_values("occurrences", ascending=False)
        .to_string(index=False)
    )