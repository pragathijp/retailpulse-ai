import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402

from ai_assistant import ask  # noqa: E402

st.set_page_config(page_title="Ask RetailPulse | RetailPulse AI", layout="wide")
st.title("💬 Ask RetailPulse")
st.caption("Answers use only pre-aggregated figures from the data marts. Every number is verified before it is shown.")

question = st.text_input("Ask about revenue, products, customers, returns or the forecast",
                         placeholder="Which products declined the most last month?")

if st.button("Ask") and question.strip():
    try:
        with st.spinner("Checking the data..."):
            result = ask(question.strip())
    except RuntimeError as exc:
        st.error(f"Assistant not configured: {exc}")
    else:
        if result["verified"]:
            st.success("All figures in this answer were verified against the data.")
        else:
            st.warning("The model's answer contained figures that could not be verified, so it was withheld.")
        st.markdown(result["answer"])
        with st.expander("Data sent to the model"):
            st.json(result["context"])
