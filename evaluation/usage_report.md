# Token Usage and Cost Analysis

## Model Provider
OpenAI

## Model Used
GPT-5.6 Luna

## Approach
The solution uses a hybrid architecture. Python performs financial calculations, forecasting, payment-plan validation, affordability checks, and final rule validation. AI is intended for request understanding and explanation where required.

## Final Dataset Run
- Total requests processed: 250
- Successful requests: 250
- Failed requests: 0
- Output rows generated: 250

## Model API Usage
- Total model calls: 0 in the final deterministic dataset generation run
- Input tokens: 0
- Output tokens: 0
- Total tokens: 0

## Token Cost
The final output generation and validation pipeline runs deterministically using the provided dataset and Python-based financial logic. Therefore, the final full-dataset run incurred:

- Estimated total model cost: $0.00
- Estimated average model cost per request: $0.00

## Validation
The generated `output.csv` was validated for:
- Exactly 250 request rows
- Exact required 8 columns
- Valid request IDs
- Valid affordability statuses
- Valid payment methods
- Safe amount bounds
- Payment-plan structure
- Installment schedules and deadlines
- Partial-payment rules
- Spending-change format

All structural and deep payment-rule validations passed successfully.