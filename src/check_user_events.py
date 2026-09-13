from data_loader import load_data
from event_resolver import get_user_events


data = load_data()

user_id = "user_26"
request_date = data["requests"][
    data["requests"]["user_id"] == user_id
].iloc[0]["request_date"]

events = get_user_events(
    data["financial_events"],
    user_id
)

print("User:", user_id)
print("Request date:", request_date.date())

print("\nEvent date range:")
print("First event:", events["event_date"].min().date())
print("Last event:", events["event_date"].max().date())

print("\nEvents after request date:")
future = events[events["event_date"] > request_date]

print("Count:", len(future))

if len(future) > 0:
    print(
        future[
            [
                "event_id",
                "event_type",
                "description",
                "amount",
                "currency",
                "event_date",
                "settlement_date",
                "status",
                "direction",
                "flexibility",
            ]
        ].to_string(index=False)
    )
else:
    print("No future events found.")