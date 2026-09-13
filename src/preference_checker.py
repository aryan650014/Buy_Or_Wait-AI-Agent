from data_loader import load_data


def get_user_payment_preferences(profiles, user_id):
    profile = profiles[
        profiles["user_id"] == user_id
    ]

    if profile.empty:
        raise ValueError(f"Profile not found: {user_id}")

    value = profile.iloc[0]["payment_methods_user_will_consider"]

    if not isinstance(value, str):
        return []

    return [
        method.strip()
        for method in value.split("|")
        if method.strip()
    ]


def is_payment_method_accepted(
    profiles,
    user_id,
    payment_method
):
    preferences = get_user_payment_preferences(
        profiles,
        user_id
    )

    return payment_method in preferences


if __name__ == "__main__":

    data = load_data()

    user_id = "user_26"

    preferences = get_user_payment_preferences(
        data["financial_profiles"],
        user_id
    )

    print("Payment Preferences")
    print("=" * 60)

    print("User:", user_id)
    print("Accepted methods:", preferences)

    print()

    for method in [
        "full_payment",
        "partial_payment",
        "installments",
        "wait"
    ]:
        print(
            f"{method:18} -> "
            f"{is_payment_method_accepted(data['financial_profiles'], user_id, method)}"
        )