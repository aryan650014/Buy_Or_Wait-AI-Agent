from data_loader import load_data
from payment_schedule import generate_payment_schedule


def check_deadline(option, desired_completion_date):
    """
    Check whether the final payment is made
    on or before the desired completion date.
    """

    schedule = generate_payment_schedule(option)

    final_payment_date = schedule[-1]["payment_date"]

    return final_payment_date <= desired_completion_date, final_payment_date


if __name__ == "__main__":

    data = load_data()

    request_id = "request_26"

    request = data["requests"][
        data["requests"]["request_id"] == request_id
    ].iloc[0]

    options = data["request_payment_options"][
        data["request_payment_options"]["request_id"] == request_id
    ]

    print("Payment Deadline Check")
    print("=" * 90)

    print("Request ID:", request_id)
    print(
        "Desired completion:",
        request["desired_completion_date"].date()
    )

    print()

    for _, option in options.iterrows():

        eligible, final_date = check_deadline(
            option,
            request["desired_completion_date"]
        )

        print(
            f"{option['payment_option_id']} | "
            f"{option['payment_method']:12} | "
            f"Final payment: {final_date.date()} | "
            f"Deadline OK: {eligible}"
        )