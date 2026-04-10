import pandas as pd
import streamlit as st
import plotly.express as px

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

    st.subheader("All price points over time")

    fig = px.scatter(
        filtered,
        x="Date",
        y="Price per month",
        color="Competitor",
        hover_data=["Plan name", "Type", "Length (in months)"]
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Raw data")
    st.dataframe(filtered, use_container_width=True)

else:
    st.info("Please upload your Excel file to start.")
