import pandas as pd
import streamlit as st

st.set_page_config(page_title="Pricing Intelligence Tool", layout="wide")

st.title("Pricing Intelligence Tool")
st.write("Upload your Excel file and explore all competitor price points from the Main sheet.")

file = st.file_uploader("Upload your Excel file", type=["xlsx"])

if file is not None:
    df = pd.read_excel(file, sheet_name="Main")

    st.sidebar.header("Filters")

    competitors = sorted(df["Competitor"].dropna().unique())
    selected_competitors = st.sidebar.multiselect(
        "Competitors",
        competitors,
        default=competitors
    )

    filtered = df.copy()

    if selected_competitors:
        filtered = filtered[filtered["Competitor"].isin(selected_competitors)]

    st.subheader("All price points")
    st.dataframe(filtered, use_container_width=True)

    st.subheader("Price per month over time")
    chart_df = filtered.copy()
    chart_df["Date"] = pd.to_datetime(chart_df["Date"], errors="coerce")
    chart_df = chart_df.dropna(subset=["Date", "Price per month"])
    chart_df = chart_df.sort_values("Date")

    if not chart_df.empty:
        st.line_chart(chart_df.set_index("Date")["Price per month"])
    else:
        st.info("No valid Date / Price per month data to chart.")

else:
    st.info("Please upload your Excel file to start.")
