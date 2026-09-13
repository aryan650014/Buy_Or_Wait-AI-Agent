import streamlit as st
import sys
from pathlib import Path

# Add code folder to Python path
BASE_DIR = Path(__file__).resolve().parent
CODE_DIR = BASE_DIR / "code"

sys.path.insert(0, str(CODE_DIR))

from data_loader import load_data
from decision_engine import analyze_request


# -----------------------------
# Page Configuration
# -----------------------------
st.set_page_config(
    page_title="Buy or Wait?",
    page_icon="💰",
    layout="wide"
)


# -----------------------------
# Load Dataset
# -----------------------------
@st.cache_data
def get_data():
    return load_data()


data = get_data()
requests = data["requests"]


# -----------------------------
# Header
# -----------------------------
st.title("💰 Buy or Wait?")
st.subheader("AI-Powered Financial Decision Agent")

st.write(
    "Analyze whether a purchase is affordable now, "
    "needs a payment plan, should be delayed, or is not recommended."
)

st.divider()


# -----------------------------
# Request Selection
# -----------------------------
st.subheader("📋 Select a Financial Request")

request_ids = requests["request_id"].tolist()

selected_request_id = st.selectbox(
    "Choose Request ID",
    request_ids
)

selected_request = requests[
    requests["request_id"] == selected_request_id
].iloc[0]


# -----------------------------
# Show Request Details
# -----------------------------
st.subheader("🛒 Purchase Details")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Request ID",
        selected_request["request_id"]
    )

with col2:
    st.metric(
        "User",
        selected_request["user_id"]
    )

with col3:
    st.metric(
        "Request Date",
        selected_request["request_date"].strftime("%Y-%m-%d")
    )


st.info(
    f"**Request:** {selected_request['request_text']}"
)


# -----------------------------
# Analyze
# -----------------------------
if st.button("🔍 Analyze Purchase", type="primary"):

    with st.spinner("Analyzing financial situation..."):

        try:
            result = analyze_request(
                selected_request,
                data
            )

            st.success("Analysis completed successfully! ✅")

            st.divider()

            # -----------------------------
            # Main Decision
            # -----------------------------
            st.subheader("🤖 AI Financial Decision")

            status = result.get(
                "affordability_status",
                "unknown"
            )

            method = result.get(
                "recommended_payment_method",
                "unknown"
            )

            safe_amount = result.get(
                "amount_safe_to_pay",
                0
            )

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    "Safe Amount",
                    f"{safe_amount:,.2f}"
                )

            with col2:
                st.metric(
                    "Affordability",
                    status.replace("_", " ").title()
                )

            with col3:
                st.metric(
                    "Payment Method",
                    method.replace("_", " ").title()
                )


            # -----------------------------
            # Payment Plan
            # -----------------------------
            st.subheader("💳 Payment Plan")

            payment_plan = result.get(
                "payment_plan",
                "none"
            )

            if payment_plan == "none":
                st.write("No payment plan required.")
            else:
                st.code(payment_plan)


            # -----------------------------
            # Earliest Full Payment
            # -----------------------------
            st.subheader("📅 Earliest Full Payment")

            earliest_date = result.get(
                "earliest_date_for_full_payment",
                ""
            )

            if earliest_date:
                st.write(
                    f"**{earliest_date}**"
                )
            else:
                st.write(
                    "Full payment is not possible within the forecast period."
                )


            # -----------------------------
            # Spending Changes
            # -----------------------------
            st.subheader("✂️ Spending Changes Needed")

            spending_changes = result.get(
                "spending_changes_needed",
                "none"
            )

            if spending_changes == "none":
                st.write("No spending changes required.")
            else:
                for change in str(spending_changes).split("|"):
                    st.write(f"• {change}")


            # -----------------------------
            # Explanation
            # -----------------------------
            st.subheader("🧠 Decision Explanation")

            explanation = result.get(
                "decision_explanation",
                "No explanation available."
            )

            st.write(explanation)


            # -----------------------------
            # Raw Result
            # -----------------------------
            with st.expander("🔎 View Complete Agent Output"):
                st.json(result)


        except Exception as e:

            st.error(
                "An error occurred while running the financial engine."
            )

            st.exception(e)