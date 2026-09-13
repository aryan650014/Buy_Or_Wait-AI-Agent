from data_loader import load_data


data = load_data()

profiles = data["financial_profiles"]
options = data["request_payment_options"]
requests = data["requests"]


merged = options.merge(
    requests[[
        "request_id",
        "user_id",
        "desired_completion_date"
    ]],
    on="request_id",
    how="left"
)

merged = merged.merge(
    profiles[[
        "user_id",
        "max_installment_months",
        "payment_methods_user_will_consider"
    ]],
    on="user_id",
    how="left"
)

installments = merged[
    merged["payment_method"] == "installments"
].copy()

print("Installment Options Analysis")
print("=" * 100)

print("Total installment options:", len(installments))

print("\nMax installment months distribution:")
print(
    profiles["max_installment_months"]
    .value_counts(dropna=False)
    .sort_index()
)

print("\nSample installment options:")
print(
    installments[[
        "request_id",
        "user_id",
        "payment_option_id",
        "payment_amount",
        "number_of_payments",
        "first_payment_date",
        "payment_frequency_days",
        "max_installment_months",
        "desired_completion_date"
    ]]
    .head(30)
    .to_string(index=False)
)