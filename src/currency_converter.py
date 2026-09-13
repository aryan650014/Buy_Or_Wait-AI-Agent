from data_loader import load_data


class CurrencyConverter:
    """
    Convert financial amounts using the dated exchange rates
    supplied in exchange_rates.csv.
    """

    def __init__(self, exchange_rates):
        self.rates = exchange_rates.copy()
        self.rates["rate_date"] = (
            self.rates["rate_date"].dt.normalize()
        )

    def _find_rate(
        self,
        from_currency,
        to_currency,
        date
    ):
        """
        Find a direct exchange rate for the exact date.
        """

        date = date.normalize()

        match = self.rates[
            (self.rates["rate_date"] == date)
            & (
                self.rates["from_currency"]
                == from_currency
            )
            & (
                self.rates["to_currency"]
                == to_currency
            )
        ]

        if not match.empty:
            return float(match.iloc[0]["rate"])

        return None

    def get_rate(
        self,
        from_currency,
        to_currency,
        date
    ):
        """
        Get conversion rate for the exact supplied date.

        First tries direct rate.
        Then tries inverse rate.

        No undated/latest rate is substituted because the
        hackathon requires dated fixed exchange rates.
        """

        from_currency = str(from_currency).strip().upper()
        to_currency = str(to_currency).strip().upper()

        if from_currency == to_currency:
            return 1.0

        date = date.normalize()

        # ---------------------------------------------
        # Direct rate
        # ---------------------------------------------

        direct_rate = self._find_rate(
            from_currency,
            to_currency,
            date
        )

        if direct_rate is not None:
            return direct_rate

        # ---------------------------------------------
        # Inverse rate
        # ---------------------------------------------

        inverse_rate = self._find_rate(
            to_currency,
            from_currency,
            date
        )

        if inverse_rate is not None:
            return 1.0 / inverse_rate

        # ---------------------------------------------
        # No valid rate
        # ---------------------------------------------

        raise ValueError(
            f"No exchange rate found for "
            f"{from_currency} -> {to_currency} "
            f"on {date.date()}"
        )

    def convert(
        self,
        amount,
        from_currency,
        to_currency,
        date
    ):
        """
        Convert an amount using the dated exchange rate.
        """

        if amount is None:
            raise ValueError(
                "Cannot convert a blank amount."
            )

        rate = self.get_rate(
            from_currency=from_currency,
            to_currency=to_currency,
            date=date
        )

        return float(amount) * rate


if __name__ == "__main__":

    data = load_data()

    converter = CurrencyConverter(
        data["exchange_rates"]
    )

    test_date = data["exchange_rates"][
        "rate_date"
    ].iloc[0]

    print()
    print("CURRENCY CONVERTER TEST")
    print("=" * 70)

    print(
        "100 USD -> EUR =",
        converter.convert(
            amount=100,
            from_currency="USD",
            to_currency="EUR",
            date=test_date
        )
    )

    print(
        "100 EUR -> USD =",
        converter.convert(
            amount=100,
            from_currency="EUR",
            to_currency="USD",
            date=test_date
        )
    )

    print(
        "100 USD -> USD =",
        converter.convert(
            amount=100,
            from_currency="USD",
            to_currency="USD",
            date=test_date
        )
    )

    print()
    print("Currency conversion test completed.")