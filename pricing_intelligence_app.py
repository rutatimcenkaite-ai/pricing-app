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

if "Competitor" in df.columns:
    df = df[df["Competitor"].notna()]
if "Price per month" in df.columns:
    df = df[df["Price per month"].notna()]

if df.empty:
    st.warning("No usable rows found in the Main sheet.")
    st.stop()

# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.header("Filters")

if st.sidebar.button("Reset filters"):
    st.rerun()

filtered = df.copy()

# -----------------------------
# Primary filters
# -----------------------------
st.sidebar.subheader("Primary")

if "Date" in filtered.columns and filtered["Date"].notna().any():
    min_date = filtered["Date"].min().date()
    max_date = filtered["Date"].max().date()

    quick_view = st.sidebar.radio(
        "Quick date view",
        ["Custom", "Last 30 days", "Last 90 days", "Last 180 days", "All data"],
        index=0,
    )

    if quick_view == "All data":
        start_default = min_date
        end_default = max_date
    elif quick_view == "Last 30 days":
        start_default = max(min_date, max_date - pd.Timedelta(days=30))
        end_default = max_date
    elif quick_view == "Last 90 days":
        start_default = max(min_date, max_date - pd.Timedelta(days=90))
        end_default = max_date
    elif quick_view == "Last 180 days":
        start_default = max(min_date, max_date - pd.Timedelta(days=180))
        end_default = max_date
    else:
        start_default = min_date
        end_default = max_date

    start_date = st.sidebar.date_input(
        "Start date",
        value=start_default,
        min_value=min_date,
        max_value=max_date,
        key="start_date",
    )

    end_date = st.sidebar.date_input(
        "End date",
        value=end_default,
        min_value=min_date,
        max_value=max_date,
        key="end_date",
    )

    if start_date > end_date:
        st.sidebar.error("Start date cannot be later than end date.")
        st.stop()

    filtered = filtered[
        filtered["Date"].dt.date.between(start_date, end_date)
    ]

if filtered.empty:
    st.warning("No rows match the selected date range.")
    st.stop()

competitor_options = (
    sorted(filtered["Competitor"].dropna().astype(str).unique().tolist())
    if "Competitor" in filtered.columns
    else []
)
selected_competitors = st.sidebar.multiselect(
    "Competitor",
    competitor_options,
    default=competitor_options[:5] if len(competitor_options) > 5 else competitor_options,
)

if selected_competitors and "Competitor" in filtered.columns:
    filtered = filtered[filtered["Competitor"].astype(str).isin(selected_competitors)]

if filtered.empty:
    st.warning("No rows match the selected competitors.")
    st.stop()

# -----------------------------
# Advanced filters
# -----------------------------
with st.sidebar.expander("Advanced filters", expanded=False):
    length_options = []
    if "Length (in months)" in filtered.columns:
        length_options = sorted(
            [int(x) for x in filtered["Length (in months)"].dropna().unique().tolist()]
        )

    selected_lengths = st.multiselect(
        "Length (in months)",
        length_options,
        default=length_options,
    )

    temp_filtered = filtered.copy()
    if selected_lengths and "Length (in months)" in temp_filtered.columns:
        temp_filtered = temp_filtered[
            temp_filtered["Length (in months)"].fillna(-1).astype(int).isin(selected_lengths)
        ]

    channel_options = (
        sorted(temp_filtered["Channel"].dropna().astype(str).unique().tolist())
        if "Channel" in temp_filtered.columns
        else []
    )
    selected_channels = st.multiselect(
        "Channel",
        channel_options,
        default=channel_options,
    )

    if selected_channels and "Channel" in temp_filtered.columns:
        temp_filtered = temp_filtered[temp_filtered["Channel"].astype(str).isin(selected_channels)]

    type_options = (
        sorted(temp_filtered["Type"].dropna().astype(str).unique().tolist())
        if "Type" in temp_filtered.columns
        else []
    )
    selected_types = st.multiselect(
        "Type",
        type_options,
        default=type_options,
    )

    if selected_types and "Type" in temp_filtered.columns:
        temp_filtered = temp_filtered[temp_filtered["Type"].astype(str).isin(selected_types)]

    plan_options = (
        sorted(temp_filtered["Plan name"].dropna().astype(str).unique().tolist())
        if "Plan name" in temp_filtered.columns
        else []
    )
    selected_plan_names = st.multiselect(
        "Plan name",
        plan_options,
        default=plan_options,
    )

# Apply advanced filters
if selected_lengths and "Length (in months)" in filtered.columns:
    filtered = filtered[
        filtered["Length (in months)"].fillna(-1).astype(int).isin(selected_lengths)
    ]

if selected_channels and "Channel" in filtered.columns:
    filtered = filtered[filtered["Channel"].astype(str).isin(selected_channels)]

if selected_types and "Type" in filtered.columns:
    filtered = filtered[filtered["Type"].astype(str).isin(selected_types)]

if selected_plan_names and "Plan name" in filtered.columns:
    filtered = filtered[filtered["Plan name"].astype(str).isin(selected_plan_names)]

if filtered.empty:
    st.warning("No rows match the current filters.")
    st.stop()

# -----------------------------
# Smart trend label
# -----------------------------
def build_trend_label(row: pd.Series, frame: pd.DataFrame) -> str:
    parts = []

    if "Competitor" in frame.columns and frame["Competitor"].nunique() > 1:
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
    st.metric(
        "Visible competitors",
        filtered["Competitor"].nunique() if "Competitor" in filtered.columns else 0,
    )

with col3:
    st.metric("Lowest price / month", f"${filtered['Price per month'].min():.2f}")

with col4:
    st.metric("Highest price / month", f"${filtered['Price per month'].max():.2f}")

# -----------------------------
# Tabs
# -----------------------------
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    ["Insights", "All price points", "Competitor comparison", "Trend lines", "Timeline", "Raw data"]
)

# -----------------------------
# Tab 1: Insights
# -----------------------------
with tab1:
    st.subheader("Insights")

    latest_date = filtered["Date"].max() if "Date" in filtered.columns and filtered["Date"].notna().any() else None
    latest_rows = filtered[filtered["Date"] == latest_date].copy() if latest_date is not None else filtered.copy()

    insight_col1, insight_col2 = st.columns(2)

    with insight_col1:
        st.markdown("#### Current snapshot")

        if not latest_rows.empty:
            cheapest_now = latest_rows.loc[latest_rows["Price per month"].idxmin()]
            expensive_now = latest_rows.loc[latest_rows["Price per month"].idxmax()]

            st.write(
                f"**Cheapest visible offer:** {cheapest_now['Competitor']} — "
                f"{cheapest_now.get('Plan name', 'Unknown')} at **${cheapest_now['Price per month']:.2f}/month**"
            )
            st.write(
                f"**Most expensive visible offer:** {expensive_now['Competitor']} — "
                f"{expensive_now.get('Plan name', 'Unknown')} at **${expensive_now['Price per month']:.2f}/month**"
            )

        range_summary = (
            filtered.groupby("Competitor", as_index=False)
            .agg(
                Min=("Price per month", "min"),
                Max=("Price per month", "max"),
                Median=("Price per month", "median"),
                Price_points=("Price per month", "count"),
            )
            .sort_values("Min")
        )

        st.dataframe(range_summary, use_container_width=True, hide_index=True)

    with insight_col2:
        st.markdown("#### Change activity")

        if "Date" in filtered.columns and filtered["Date"].notna().any():
            trend_activity = (
                filtered.sort_values("Date")
                .groupby(["Competitor", "Trend label"])["Price per month"]
                .nunique()
                .reset_index(name="Distinct prices")
            )

            change_summary = (
                trend_activity.groupby("Competitor", as_index=False)["Distinct prices"]
                .sum()
                .sort_values("Distinct prices", ascending=False)
            )

            if not change_summary.empty:
                most_active = change_summary.iloc[0]
                st.write(
                    f"**Most pricing movement:** {most_active['Competitor']} "
                    f"with **{int(most_active['Distinct prices'])}** distinct visible price points."
                )

                st.dataframe(change_summary, use_container_width=True, hide_index=True)

        if "Length (in months)" in filtered.columns:
            cheapest_by_length = (
                filtered.dropna(subset=["Length (in months)", "Price per month"])
                .sort_values(["Length (in months)", "Price per month"])
                .groupby("Length (in months)", as_index=False)
                .first()[["Length (in months)", "Competitor", "Plan name", "Price per month"]]
            )

            if not cheapest_by_length.empty:
                st.markdown("#### Cheapest offer by length")
                st.dataframe(cheapest_by_length, use_container_width=True, hide_index=True)

# -----------------------------
# Tab 2: All price points
# -----------------------------
with tab2:
    st.subheader("All visible price points by competitor")

    st.vega_lite_chart(
        filtered,
        {
            "mark": {"type": "circle", "size": 90, "opacity": 0.75},
            "encoding": {
                "x": {
                    "field": "Competitor",
                    "type": "nominal",
                    "sort": sorted(filtered["Competitor"].dropna().astype(str).unique().tolist()),
                    "title": "Competitor",
                    "axis": {"labelAngle": -35},
                },
                "y": {
                    "field": "Price per month",
                    "type": "quantitative",
                    "title": "Price per month",
                    "axis": {"format": "$.2f"},
                },
                "color": {
                    "field": "Competitor",
                    "type": "nominal",
                    "legend": None,
                },
                "tooltip": [
                    {"field": "Date", "type": "temporal", "format": "%Y-%m-%d"},
                    {"field": "Competitor", "type": "nominal"},
                    {"field": "Channel", "type": "nominal"},
                    {"field": "Type", "type": "nominal"},
                    {"field": "Plan name", "type": "nominal"},
                    {"field": "Length (in months)", "type": "quantitative"},
                    {"field": "Price per month", "type": "quantitative", "format": "$.2f"},
                    {"field": "Total price", "type": "quantitative", "format": "$.2f"},
                ],
            },
            "height": 500,
        },
        use_container_width=True,
    )

# -----------------------------
# Tab 3: Competitor comparison
# -----------------------------
with tab3:
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

    st.dataframe(summary, use_container_width=True, hide_index=True)

# -----------------------------
# Tab 4: Trend lines
# -----------------------------
with tab4:
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
        available_labels = sorted(trend_df["Trend label"].dropna().astype(str).unique().tolist())

        default_lines = available_labels[:10] if len(available_labels) > 10 else available_labels
        selected_line_labels = st.multiselect(
            "Choose lines to display",
            available_labels,
            default=default_lines,
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
                    "labelOverlap": "greedy",
                },
            },
            "y": {
                "field": metric_choice,
                "type": "quantitative",
                "title": metric_choice,
                "axis": {"format": "$.2f"},
            },
            "tooltip": [
                {"field": "Date", "type": "temporal", "format": "%Y-%m-%d"},
                {"field": "Competitor", "type": "nominal"},
                {"field": "Channel", "type": "nominal"},
                {"field": "Type", "type": "nominal"},
                {"field": "Plan name", "type": "nominal"},
                {"field": "Length (in months)", "type": "quantitative"},
                {"field": metric_choice, "type": "quantitative", "format": "$.2f"},
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
            competitor_list = sorted(trend_df["Competitor"].dropna().astype(str).unique().tolist())
            for comp in competitor_list:
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
# Tab 5: Timeline
# -----------------------------
with tab5:
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
                            "labelOverlap": "greedy",
                        },
                    },
                    "y": {
                        "field": "Price per month",
                        "type": "quantitative",
                        "title": "Price per month",
                        "axis": {"format": "$.2f"},
                    },
                    "color": {"field": "Competitor", "type": "nominal"},
                    "tooltip": [
                        {"field": "Date", "type": "temporal", "format": "%Y-%m-%d"},
                        {"field": "Competitor", "type": "nominal"},
                        {"field": "Channel", "type": "nominal"},
                        {"field": "Type", "type": "nominal"},
                        {"field": "Plan name", "type": "nominal"},
                        {"field": "Length (in months)", "type": "quantitative"},
                        {"field": "Price per month", "type": "quantitative", "format": "$.2f"},
                        {"field": "Total price", "type": "quantitative", "format": "$.2f"},
                    ],
                },
                "height": 500,
            },
            use_container_width=True,
        )

# -----------------------------
# Tab 6: Raw data
# -----------------------------
with tab6:
    st.subheader("Raw filtered export")
    st.dataframe(filtered, use_container_width=True)

    csv_data = filtered.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download filtered data as CSV",
        data=csv_data,
        file_name="pricing_filtered.csv",
        mime="text/csv",
    )

with st.expander("Check column meaning"):
    st.write(
        "This app uses the Excel columns exactly as they appear in the Main sheet. "
        "If values like Duo / Family / Individual are appearing under Plan name instead of Type, "
        "that usually means the source rows in the Excel file are structured that way. "
        "The next step would be to add a normalization rule for specific competitors if needed."
    )
