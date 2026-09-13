from datetime import timedelta
import pandas as pd

from data_loader import load_data


def generate_payment_schedule(option):
    """
    Generate all payment dates for a payment option.
    """

    number_of_payments = int(option["number_of_payments"])
    first_payment_date = option["first_payment_date"]
    frequency_days = option["payment_frequency_days"]
    payment_amount = option["payment_amount"]

    schedule = []

    for i in range(number_of_payments):

        if pd.isna(frequency_days):
            payment_date = first_payment_date
        else:
            payment_date = first_payment_date + timedelta(
                days=int(frequency_days) * i
            )

        schedule.append({
            "payment_number": i + 1,
            "payment_date": payment_date,
            "payment_amount": payment_amount
        })

    return schedule


if __name__ == "__main__":

    data = load_data()

    request_id = "request_26"

    options = data["request_payment_options"][
        data["request_payment_options"]["request_id"] == request_id
    ]

    for _, option in options.iterrows():

        print("\n" + "=" * 80)
        print("Payment Option:", option["payment_option_id"])
        print("Method:", option["payment_method"])
        print("Number of payments:", int(option["number_of_payments"]))
        print("Payment amount:", f"{option['payment_amount']:,.2f}")

        schedule = generate_payment_schedule(option)

        print("\nSchedule:")

        for payment in schedule:
            print(
                f"Payment {payment['payment_number']:2d} | "
                f"{payment['payment_date'].date()} | "
                f"{payment['payment_amount']:,.2f}"
            )