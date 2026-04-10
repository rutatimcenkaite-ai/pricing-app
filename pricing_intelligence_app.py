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
df.columns = [str(col).strip() for col in df.columns]

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

df = df[df["Competitor"].notna()]
df = df[df["Price per month"].notna()]

if df.empty:
    st.warning("No usable rows found in the Main sheet.")
    st.stop()

# -----------------------------
# Cascading filters
# -----------------------------
st.sidebar.header("Filters")

base_df = df.copy()

# 1. Competitor
competitor_options = sorted(base_df["Competitor"].dropna().unique().tolist())
selected_competitors = st.sidebar.multiselect(
    "Competitors",
    competitor_options,
    default=competitor_options,
)

step_df = base_df.copy()
if selected_competitors:
    step_df = step_df[step_df["Competitor"].isin(selected_competitors)]

# 2. Channel
channel_options = (
    sorted(step_df["Channel"].dropna().unique().tolist())
    if "Channel" in step_df.columns
    else []
)
selected_channels = st.sidebar.multiselect(
    "Channels",
    channel_options,
    default=channel_options,
)

if selected_channels and "Channel" in step_df.columns:
    step_df = step_df[step_df["Channel"].isin(selected_channels)]

# 3. Plan name
plan_options = (
    sorted(step_df["Plan name"].dropna().unique().tolist())
    if "Plan name" in step_df.columns
    else []
)
selected_plan_names = st.sidebar.multiselect(
    "Plan names",
    plan_options,
    default=plan_options,
)

if selected_plan_names and "Plan name" in step_df.columns:
    step_df = step_df[step_df["Plan name"].isin(selected_plan_names)]

# 4. Type
type_options = (
    sorted(step_df["Type"].dropna().unique().tolist())
    if "Type" in step_df.columns
    else []
)
selected_types = st.sidebar.multiselect(
    "Types",
    type_options,
    default=type_options,
)

if selected_types and "Type" in step_df.columns:
    step_df = step_df[step_df["Type"].isin(selected_types)]

# 5. Length
length_options = []
if "Length (in months)" in step_df.columns:
    length_options = sorted(
        [int(x) for x in step_df["Length (in months)"].dropna().unique().tolist()]
    )

selected_month_lengths = st.sidebar.multiselect(
    "Length (in months)",
    length_options,
    default=length_options,
)

if selected_month_lengths and "Length (in months)" in step_df.columns:
    step_df = step_df[
        step_df["Length (in months)"].fillna(-1).astype(int).isin(selected_month_lengths)
    ]

# 6. Easier date filters: Year + Month
filtered = step_df.copy()

if "Date" in filtered.columns and filtered["Date"].notna().any():
    filtered["Year"] = filtered["Date"].dt.year
    filtered["Month"] = filtered["Date"].dt.month

    year_options = sorted(filtered["Year"].dropna().astype(int).unique().tolist())
    selected_years = st.sidebar.multiselect(
        "Years",
        year_options,
        default=year_options,
    )

    if selected_years:
        filtered = filtered[filtered["Year"].isin(selected_years)]

    month_options = sorted(filtered["Month"].dropna().astype(int).unique().tolist())
    month_name_map = {
        1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
        5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
        9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
    }

    selected_months = st.sidebar.multiselect(
        "Months",
        month_options,
        default=month_options,
        format_func=lambda x: month_name_map.get(x, str(x)),
    )

    if selected_months:
        filtered = filtered[filtered["Month"].isin(selected_months)]

if filtered.empty:
    st.warning("No rows match your filters.")
    st.stop()

# -----------------------------
# Smart trend label
# -----------------------------
def build_trend_label(row, frame):
    parts = []

    if frame["Competitor"].nunique() > 1:
        parts.append(str(row["Competitor"]))

    if "Plan name" in frame.columns and frame["Plan name"].nunique() > 1:
        parts.append(str(row["Plan name"]))

    if "Type" in frame.columns and frame["Type"].nunique() > 1:
        parts.append(str(row["Type"]))

    if "Length (in months)" in frame.columns and frame["Length (in months)"].nunique() > 1:
        try:
            parts.append(f"{int(row['Length (in months)'])}m")
        except Exception:
            parts.append(str(row["Length (in months)"]))

    if not parts:
        return str(row["Competitor"])

    return " | ".join(parts)

filtered["Trend label"] = filtered.apply(lambda row: build_trend_label(row, filtered), axis=1)

# -----------------------------
# KPI cards
# -----------------------------
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Visible rows", f"{len(filtered):,}")

with col2:
    st.metric("Visible competitors", filtered["Competitor"].nunique())

with col3:
    st.metric("Lowest price / month", f"${filtered['Price per month'].min():.2f}")

with col4:
    st.metric("Highest price / month", f"${filtered['Price per month'].max():.2f}")

# -----------------------------
# Tabs
# -----------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["All price points", "Competitor comparison", "Trend lines", "Timeline", "Raw data"]
)

# -----------------------------
# Tab 1: All price points
# -----------------------------
with tab1:
    st.subheader("All visible price points by competitor")

    scatter_df = filtered.copy()

    st.vega_lite_chart(
        scatter_df,
        {
            "mark": {"type": "circle", "size": 90, "opacity": 0.75},
            "encoding": {
                "x": {
                    "field": "Competitor",
                    "type": "nominal",
                    "sort": sorted(scatter_df["Competitor"].unique().tolist()),
                    "title": "Competitor",
                    "axis": {"labelAngle": -35},
                },
                "y": {
                    "field": "Price per month",
                    "type": "quantitative",
                    "title": "Price per month",
                },
                "color": {
                    "field": "Competitor",
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
                    {"field": "Date", "type": "temporal", "format": "%Y-%m-%d"},
                ],
            },
            "height": 500,
        },
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

# -----------------------------
# Tab 3: Trend lines
# -----------------------------
with tab3:
    st.subheader("Pricing trend lines over time")

    metric_choice = st.selectbox(
        "Metric",
        ["Price per month", "Total price"],
        index=0,
    )

    trend_df = filtered.dropna(subset=["Date", metric_choice]).copy()
    trend_df = trend_df.sort_values("Date")

    if trend_df.empty:
        st.info("No valid Date / metric rows available for trend lines.")
    else:
        available_labels = sorted(trend_df["Trend label"].unique().tolist())

        selected_line_labels = st.multiselect(
            "Choose lines to display",
            available_labels,
            default=available_labels,
        )

        if selected_line_labels:
            trend_df = trend_df[trend_df["Trend label"].isin(selected_line_labels)]

        chart_mode = st.radio(
            "Chart mode",
            ["Single combined chart", "One chart per competitor"],
            horizontal=True,
        )

        base_encoding = {
            "x": {
                "field": "Date",
                "type": "temporal",
                "title": "Scrape date",
                "axis": {
                    "format": "%Y-%m-%d",
                    "labelAngle": -45,
                    "labelOverlap": "greedy"
                },
            },
            "y": {
                "field": metric_choice,
                "type": "quantitative",
                "title": metric_choice,
            },
            "tooltip": [
                {"field": "Date", "type": "temporal", "format": "%Y-%m-%d"},
                {"field": "Competitor", "type": "nominal"},
                {"field": "Plan name", "type": "nominal"},
                {"field": "Type", "type": "nominal"},
                {"field": "Length (in months)", "type": "quantitative"},
                {"field": metric_choice, "type": "quantitative"},
            ],
        }

        if chart_mode == "Single combined chart":
            st.vega_lite_chart(
                trend_df,
                {
                    "mark": {"type": "line", "point": True},
                    "encoding": {
                        **base_encoding,
                        "color": {
                            "field": "Trend label",
                            "type": "nominal",
                            "title": "Line",
                        },
                    },
                    "height": 500,
                },
                use_container_width=True,
            )
        else:
            for comp in sorted(trend_df["Competitor"].dropna().unique().tolist()):
                comp_df = trend_df[trend_df["Competitor"] == comp].copy()
                st.markdown(f"### {comp}")

                st.vega_lite_chart(
                    comp_df,
                    {
                        "mark": {"type": "line", "point": True},
                        "encoding": {
                            **base_encoding,
                            "color": {
                                "field": "Trend label",
                                "type": "nominal",
                                "title": "Line",
                            },
                        },
                        "height": 350,
                    },
                    use_container_width=True,
                )

# -----------------------------
# Tab 4: Timeline
# -----------------------------
with tab4:
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
                    "x": {
                        "field": "Date",
                        "type": "temporal",
                        "title": "Scrape date",
                        "axis": {
                            "format": "%Y-%m-%d",
                            "labelAngle": -45,
                            "labelOverlap": "greedy"
                        },
                    },
                    "y": {
                        "field": "Price per month",
                        "type": "quantitative",
                        "title": "Price per month",
                    },
                    "color": {"field": "Competitor", "type": "nominal"},
                    "tooltip": [
                        {"field": "Date", "type": "temporal", "format": "%Y-%m-%d"},
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
# Tab 5: Raw data
# -----------------------------
with tab5:
    st.subheader("Raw filtered export")
    export_df = filtered.copy()

    if "Year" in export_df.columns:
        export_df = export_df.drop(columns=["Year"])
    if "Month" in export_df.columns:
        export_df = export_df.drop(columns=["Month"])

    st.dataframe(export_df, use_container_width=True)

    csv_data = export_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download filtered data as CSV",
        data=csv_data,
        file_name="pricing_filtered.csv",
        mime="text/csv",
    )
