import pandas as pd
import streamlit as st

st.set_page_config(page_title="Pricing Intelligence Tool", layout="wide")

MAIN_SHEET = "Main"

st.title("Pricing Intelligence Tool")
st.caption("Explore all competitor price points from the Main sheet without forcing averages.")

uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx"])

if uploaded_file is None:
    st.info("Please upload your Excel file to start.")
    st.stop()

# -----------------------------
# Load data
# -----------------------------
df = pd.read_excel(uploaded_file, sheet_name=MAIN_SHEET)

# Clean column names just in case
df.columns = [str(col).strip() for col in df.columns]

# Convert types safely
if "Date" in df.columns:
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

numeric_cols = [
    "Length (in months)",
    "Price per month",
    "Total price",
    "Discount",
    "Recurring total price",
    "VAT",
]

for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

text_cols = [
    "Country",
    "Competitor",
    "Channel",
    "Plan name",
    "Type",
    "Additional months/benefits",
    "Any additional comments",
]

for col in text_cols:
    if col in df.columns:
        df[col] = df[col].fillna("Unknown").astype(str).str.strip()
        df.loc[df[col] == "", col] = "Unknown"

# Keep only rows with a competitor and price point
if "Competitor" in df.columns and "Price per month" in df.columns:
    df = df[df["Competitor"].notna()]
    df = df[df["Price per month"].notna()]

if df.empty:
    st.warning("No usable rows found in the Main sheet.")
    st.stop()

# -----------------------------
# Sidebar filters
# -----------------------------
st.sidebar.header("Filters")

def multiselect_filter(label, column_name):
    if column_name not in df.columns:
        return []
    options = sorted(df[column_name].dropna().astype(str).unique().tolist())
    return st.sidebar.multiselect(label, options, default=options)

selected_competitors = multiselect_filter("Competitors", "Competitor")
selected_channels = multiselect_filter("Channels", "Channel")
selected_plan_names = multiselect_filter("Plan names", "Plan name")
selected_types = multiselect_filter("Types", "Type")

selected_month_lengths = []
if "Length (in months)" in df.columns:
    month_options = sorted(
        [int(x) for x in df["Length (in months)"].dropna().unique().tolist()]
    )
    selected_month_lengths = st.sidebar.multiselect(
        "Length (in months)",
        month_options,
        default=month_options,
    )

if "Date" in df.columns and df["Date"].notna().any():
    min_date = df["Date"].min().date()
    max_date = df["Date"].max().date()
    selected_date_range = st.sidebar.date_input(
        "Date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
else:
    selected_date_range = None

# -----------------------------
# Apply filters
# -----------------------------
filtered = df.copy()

if selected_competitors and "Competitor" in filtered.columns:
    filtered = filtered[filtered["Competitor"].astype(str).isin(selected_competitors)]

if selected_channels and "Channel" in filtered.columns:
    filtered = filtered[filtered["Channel"].astype(str).isin(selected_channels)]

if selected_plan_names and "Plan name" in filtered.columns:
    filtered = filtered[filtered["Plan name"].astype(str).isin(selected_plan_names)]

if selected_types and "Type" in filtered.columns:
    filtered = filtered[filtered["Type"].astype(str).isin(selected_types)]

if selected_month_lengths and "Length (in months)" in filtered.columns:
    filtered = filtered[
        filtered["Length (in months)"].fillna(-1).astype(int).isin(selected_month_lengths)
    ]

if (
    selected_date_range is not None
    and isinstance(selected_date_range, tuple)
    and len(selected_date_range) == 2
    and "Date" in filtered.columns
):
    start_date = pd.to_datetime(selected_date_range[0])
    end_date = pd.to_datetime(selected_date_range[1])
    filtered = filtered[filtered["Date"].between(start_date, end_date)]

if filtered.empty:
    st.warning("No rows match your filters.")
    st.stop()

# -----------------------------
# KPI cards
# -----------------------------
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Visible rows", f"{len(filtered):,}")

with col2:
    st.metric("Visible competitors", filtered["Competitor"].nunique())

with col3:
    min_price = filtered["Price per month"].min()
    st.metric("Lowest price / month", f"${min_price:.2f}")

with col4:
    max_price = filtered["Price per month"].max()
    st.metric("Highest price / month", f"${max_price:.2f}")

# -----------------------------
# Tabs
# -----------------------------
tab1, tab2, tab3, tab4 = st.tabs(
    ["All price points", "Competitor comparison", "Timeline", "Raw data"]
)

# -----------------------------
# Tab 1: All price points
# -----------------------------
with tab1:
    st.subheader("All visible price points by competitor")

    scatter_df = filtered.copy()
    scatter_df["Competitor label"] = scatter_df["Competitor"].astype(str)

    st.vega_lite_chart(
        scatter_df,
        {
            "mark": {"type": "circle", "size": 90, "opacity": 0.75},
            "encoding": {
                "x": {
                    "field": "Competitor label",
                    "type": "nominal",
                    "sort": sorted(scatter_df["Competitor label"].unique().tolist()),
                    "title": "Competitor",
                    "axis": {"labelAngle": -35},
                },
                "y": {
                    "field": "Price per month",
                    "type": "quantitative",
                    "title": "Price per month",
                },
                "color": {
                    "field": "Competitor label",
                    "type": "nominal",
                    "legend": None,
                },
                "tooltip": [
                    {"field": "Competitor", "type": "nominal"},
                    {"field": "Plan name", "type": "nominal"},
                    {"field": "Channel", "type": "nominal"},
                    {"field": "Type", "type": "nominal"},
                    {"field": "Length (in months)", "type": "quantitative"},
                    {"field": "Price per month", "type": "quantitative"},
                    {"field": "Total price", "type": "quantitative"},
                    {"field": "Date", "type": "temporal"},
                ],
            },
            "height": 500,
        },
        use_container_width=True,
    )

    st.subheader("Visible price point table")
    display_cols = [
        "Date",
        "Country",
        "Competitor",
        "Channel",
        "Plan name",
        "Type",
        "Length (in months)",
        "Price per month",
        "Total price",
        "Discount",
        "Additional months/benefits",
        "Recurring total price",
        "Any additional comments",
    ]
    display_cols = [c for c in display_cols if c in filtered.columns]

    st.dataframe(
        filtered[display_cols].sort_values(
            by=[c for c in ["Competitor", "Date", "Price per month"] if c in filtered.columns],
            ascending=[True, False, True][:len([c for c in ["Competitor", "Date", "Price per month"] if c in filtered.columns])]
        ),
        use_container_width=True,
    )

# -----------------------------
# Tab 2: Competitor comparison
# -----------------------------
with tab2:
    st.subheader("Competitor comparison summary")

    summary = (
        filtered.groupby("Competitor", as_index=False)
        .agg(
            price_points=("Price per month", "count"),
            min_price=("Price per month", "min"),
            median_price=("Price per month", "median"),
            max_price=("Price per month", "max"),
            min_total_price=("Total price", "min"),
            max_total_price=("Total price", "max"),
        )
        .sort_values("min_price")
    )

    st.dataframe(summary, use_container_width=True)

    st.subheader("Price range by competitor")

    range_chart_df = summary.copy()
    st.vega_lite_chart(
        range_chart_df,
        {
            "layer": [
                {
                    "mark": {"type": "rule", "strokeWidth": 3},
                    "encoding": {
                        "y": {
                            "field": "Competitor",
                            "type": "nominal",
                            "sort": list(range_chart_df["Competitor"]),
                            "title": "",
                        },
                        "x": {
                            "field": "min_price",
                            "type": "quantitative",
                            "title": "Price per month",
                        },
                        "x2": {"field": "max_price"},
                        "tooltip": [
                            {"field": "Competitor", "type": "nominal"},
                            {"field": "price_points", "type": "quantitative"},
                            {"field": "min_price", "type": "quantitative"},
                            {"field": "median_price", "type": "quantitative"},
                            {"field": "max_price", "type": "quantitative"},
                        ],
                    },
                },
                {
                    "mark": {"type": "point", "filled": True, "size": 90},
                    "encoding": {
                        "y": {
                            "field": "Competitor",
                            "type": "nominal",
                            "sort": list(range_chart_df["Competitor"]),
                            "title": "",
                        },
                        "x": {"field": "median_price", "type": "quantitative"},
                        "tooltip": [
                            {"field": "Competitor", "type": "nominal"},
                            {"field": "price_points", "type": "quantitative"},
                            {"field": "min_price", "type": "quantitative"},
                            {"field": "median_price", "type": "quantitative"},
                            {"field": "max_price", "type": "quantitative"},
                        ],
                    },
                },
            ],
            "height": 420,
        },
        use_container_width=True,
    )

# -----------------------------
# Tab 3: Timeline
# -----------------------------
with tab3:
    st.subheader("All visible price points over time")

    timeline_df = filtered.dropna(subset=["Date", "Price per month"]).copy()
    timeline_df = timeline_df.sort_values("Date")

    if timeline_df.empty:
        st.info("No valid Date / Price per month rows available for timeline view.")
    else:
        st.vega_lite_chart(
            timeline_df,
            {
                "mark": {"type": "circle", "size": 70, "opacity": 0.7},
                "encoding": {
                    "x": {"field": "Date", "type": "temporal", "title": "Date"},
                    "y": {
                        "field": "Price per month",
                        "type": "quantitative",
                        "title": "Price per month",
                    },
                    "color": {"field": "Competitor", "type": "nominal"},
                    "tooltip": [
                        {"field": "Date", "type": "temporal"},
                        {"field": "Competitor", "type": "nominal"},
                        {"field": "Plan name", "type": "nominal"},
                        {"field": "Channel", "type": "nominal"},
                        {"field": "Type", "type": "nominal"},
                        {"field": "Length (in months)", "type": "quantitative"},
                        {"field": "Price per month", "type": "quantitative"},
                        {"field": "Total price", "type": "quantitative"},
                    ],
                },
                "height": 500,
            },
            use_container_width=True,
        )

# -----------------------------
# Tab 4: Raw data
# -----------------------------
with tab4:
    st.subheader("Raw filtered export")
    st.dataframe(filtered, use_container_width=True)

    csv_data = filtered.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download filtered data as CSV",
        data=csv_data,
        file_name="pricing_filtered.csv",
        mime="text/csv",
    )
