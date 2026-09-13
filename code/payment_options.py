from data_loader import load_data


def get_request_payment_options(payment_options, request_id):
    options = payment_options[
        payment_options["request_id"] == request_id
    ].copy()

    return options.sort_values("payment_option_id")


if __name__ == "__main__":

    data = load_data()

    request_id = "request_26"

    options = get_request_payment_options(
        data["request_payment_options"],
        request_id
    )

    print("Payment Options")
    print("=" * 90)

    print("Request ID:", request_id)
    print("Number of options:", len(options))
    print()

    if options.empty:
        print("No payment options found.")
    else:
        for _, option in options.iterrows():

            print(
                f"Option ID: {option['payment_option_id']}"
            )
            print(
                f"Method: {option['payment_method']}"
            )
            print(
                f"Payment amount: {option['payment_amount']:,.2f}"
            )
            print(
                f"Number of payments: {option['number_of_payments']}"
            )
            print(
                f"First payment date: "
                f"{option['first_payment_date'].date()}"
            )
            print(
                f"Frequency: "
                f"{option['payment_frequency_days']} days"
            )
            print(
                f"Financing fee: "
                f"{option['financing_fee']:,.2f}"
            )
            print(
                f"Total payable: "
                f"{option['total_payable_amount']:,.2f}"
            )
            print("-" * 90)