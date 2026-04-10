import pandas as pd
import streamlit as st
import plotly.express as px

st.title("Pricing Intelligence Tool")

# Load file

file = st.file_uploader("Upload your Excel file", type=["xlsx"])

if file:
df = pd.read_excel(file, sheet_name="Main")

```
st.sidebar.header("Filters")

competitors = st.sidebar.multiselect(
    "Competitors",
    df["Competitor"].dropna().unique()
)

filtered = df.copy()

if competitors:
    filtered = filtered[filtered["Competitor"].isin(competitors)]

st.subheader("All price points")

fig = px.scatter(
    filtered,
    x="Date",
    y="Price per month",
    color="Competitor",
    hover_data=["Plan name", "Type", "Length (in months)"]
)

st.plotly_chart(fig)

st.subheader("Raw data")
st.dataframe(filtered)
```
