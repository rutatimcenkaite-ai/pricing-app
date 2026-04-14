import pandas as pd
import streamlit as st

st.set_page_config(page_title="Pricing Intelligence Tool", layout="wide")

MAIN_SHEET = "Main"

DEFAULT_COMPETITORS = ["NordVPN", "ExpressVPN", "ProtonVPN"]
EVENTS = {
    "Default": "2025-09-22",
    "Black Friday": "2025-11-28",
    "Christmas": "2025-12-22",
    "2026 Cool-off": "2026-01-10",
    "Valentine's Day": "2026-02-04",
    "Spring sale": "2026-03-24",
}
TWO_YEAR_LENGTHS = [24, 27, 28]

COMPETITOR_COLOR_SCALE = {
    "domain": ["NordVPN", "ExpressVPN", "ProtonVPN", "Proton", "Surfshark", "CyberGhost", "PIA"],
    "range": ["#4285f4", "#EA4335", "#34A853", "#34A853", "#FABB05", "#A142F4", "#00ACC1"],
}


def fmt_currency(value):
    if pd.isna(value):
        return ""
    return f"${value:.2f}"


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
# Sidebar filters
# -----------------------------
st.sidebar.header("Filters")

if st.sidebar.button("Reset filters"):
    st.rerun()

filtered = df.copy()

# Start / End date
if "Date" in filtered.columns and filtered["Date"].notna().any():
    min_date = filtered["Date"].min().date()
    max_date = filtered["Date"].max().date()

    start_date = st.sidebar.date_input(
        "Start date",
        value=min_date,
        min_value=min_date,
        max_value=max_date,
        key="start_date",
    )

    end_date = st.sidebar.date_input(
        "End date",
        value=max_date,
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

# Competitor
competitor_options = (
    sorted(filtered["Competitor"].dropna().astype(str).unique().tolist())
    if "Competitor" in filtered.columns
    else []
)
default_competitors = [c for c in DEFAULT_COMPETITORS if c in competitor_options]
if not default_competitors:
    default_competitors = competitor_options[:3] if len(competitor_options) >= 3 else competitor_options

selected_competitors = st.sidebar.multiselect(
    "Competitor",
    competitor_options,
    default=default_competitors,
)

if selected_competitors and "Competitor" in filtered.columns:
    filtered = filtered[filtered["Competitor"].astype(str).isin(selected_competitors)]

if filtered.empty:
    st.warning("No rows match the selected competitors.")
    st.stop()

# Length
length_options = []
if "Length (in months)" in filtered.columns:
    length_options = sorted(
        [int(x) for x in filtered["Length (in months)"].dropna().unique().tolist()]
    )

selected_lengths = st.sidebar.multiselect(
    "Length (in months)",
    length_options,
    default=length_options,
)

if selected_lengths and "Length (in months)" in filtered.columns:
    filtered = filtered[
        filtered["Length (in months)"].fillna(-1).astype(int).isin(selected_lengths)
    ]

if filtered.empty:
    st.warning("No rows match the selected lengths.")
    st.stop()

# Channel
channel_options = (
    sorted(filtered["Channel"].dropna().astype(str).unique().tolist())
    if "Channel" in filtered.columns
    else []
)
selected_channels = st.sidebar.multiselect(
    "Channel",
    channel_options,
    default=channel_options,
)

if selected_channels and "Channel" in filtered.columns:
    filtered = filtered[filtered["Channel"].astype(str).isin(selected_channels)]

if filtered.empty:
    st.warning("No rows match the selected channels.")
    st.stop()

# Type
type_options = (
    sorted(filtered["Type"].dropna().astype(str).unique().tolist())
    if "Type" in filtered.columns
    else []
)
selected_types = st.sidebar.multiselect(
    "Type",
    type_options,
    default=type_options,
)

if selected_types and "Type" in filtered.columns:
    filtered = filtered[filtered["Type"].astype(str).isin(selected_types)]

if filtered.empty:
    st.warning("No rows match the selected types.")
    st.stop()

# Plan name
plan_options = (
    sorted(filtered["Plan name"].dropna().astype(str).unique().tolist())
    if "Plan name" in filtered.columns
    else []
)
selected_plan_names = st.sidebar.multiselect(
    "Plan name",
    plan_options,
    default=plan_options,
)

if selected_plan_names and "Plan name" in filtered.columns:
    filtered = filtered[filtered["Plan name"].astype(str).isin(selected_plan_names)]

if filtered.empty:
    st.warning("No rows match the selected plan names.")
    st.stop()

# -----------------------------
# Labels and summary fields
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

latest_in_file = df["Date"].max() if "Date" in df.columns and df["Date"].notna().any() else None
latest_visible = filtered["Date"].max() if "Date" in filtered.columns and filtered["Date"].notna().any() else None

# -----------------------------
# KPI cards
# -----------------------------
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Visible rows", f"{len(filtered):,}")

with col2:
    st.metric("Visible competitors", filtered["Competitor"].nunique())

with col3:
    st.metric("Lowest visible price / month", fmt_currency(filtered["Price per month"].min()))

with col4:
    st.metric("Highest visible price / month", fmt_currency(filtered["Price per month"].max()))

meta1, meta2 = st.columns(2)
with meta1:
    st.caption(f"Latest scrape in file: {latest_in_file.strftime('%Y-%m-%d') if latest_in_file is not None else 'N/A'}")
with meta2:
    st.caption(f"Latest visible scrape: {latest_visible.strftime('%Y-%m-%d') if latest_visible is not None else 'N/A'}")

# -----------------------------
# Tabs
# -----------------------------
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
    ["Insights", "All price points", "Competitor comparison", "Trend lines", "Timeline", "Event view", "Raw data"]
)

# -----------------------------
# Tab 1: Insights
# -----------------------------
with tab1:
    st.subheader("Insights")
    st.caption("Readable summary of the currently visible data.")

    latest_rows = filtered[filtered["Date"] == latest_visible].copy() if latest_visible is not None else filtered.copy()

    insight_col1, insight_col2 = st.columns(2)

    with insight_col1:
        st.markdown("#### Snapshot")
        if not latest_rows.empty:
            cheapest_now = latest_rows.loc[latest_rows["Price per month"].idxmin()]
            highest_now = latest_rows.loc[latest_rows["Price per month"].idxmax()]

            st.write(
                f"**Cheapest visible offer:** {cheapest_now['Competitor']} "
                f"({cheapest_now.get('Plan name', 'Unknown')}, {cheapest_now.get('Type', 'Unknown')}) "
                f"at **{fmt_currency(cheapest_now['Price per month'])}/month**"
            )
            st.write(
                f"**Highest visible offer:** {highest_now['Competitor']} "
                f"({highest_now.get('Plan name', 'Unknown')}, {highest_now.get('Type', 'Unknown')}) "
                f"at **{fmt_currency(highest_now['Price per month'])}/month**"
            )

        simple_summary = (
            filtered.sort_values(["Competitor", "Price per month", "Date"])
            .groupby("Competitor", as_index=False)
            .first()[["Competitor", "Plan name", "Type", "Price per month", "Date"]]
            .rename(
                columns={
                    "Plan name": "Cheapest plan",
                    "Type": "Cheapest type",
                    "Price per month": "Lowest visible monthly price",
                    "Date": "Date of cheapest visible offer",
                }
            )
        )
        simple_summary["Lowest visible monthly price"] = simple_summary["Lowest visible monthly price"].map(fmt_currency)

        st.markdown("#### Cheapest visible offer by competitor")
        st.dataframe(simple_summary, use_container_width=True, hide_index=True)

    with insight_col2:
        st.markdown("#### Price ranges")
        range_summary = (
            filtered.groupby("Competitor", as_index=False)
            .agg(
                Lowest_visible_monthly_price=("Price per month", "min"),
                Highest_visible_monthly_price=("Price per month", "max"),
                Cheapest_plan=("Plan name", "first"),
                Latest_visible_scrape=("Date", "max"),
            )
            .sort_values("Lowest_visible_monthly_price")
        )
        range_summary["Lowest_visible_monthly_price"] = range_summary["Lowest_visible_monthly_price"].map(fmt_currency)
        range_summary["Highest_visible_monthly_price"] = range_summary["Highest_visible_monthly_price"].map(fmt_currency)

        st.dataframe(range_summary, use_container_width=True, hide_index=True)

        if "Length (in months)" in filtered.columns:
            cheapest_by_length = (
                filtered.dropna(subset=["Length (in months)", "Price per month"])
                .sort_values(["Length (in months)", "Price per month"])
                .groupby("Length (in months)", as_index=False)
                .first()[["Length (in months)", "Competitor", "Plan name", "Type", "Price per month"]]
            )
            cheapest_by_length["Price per month"] = cheapest_by_length["Price per month"].map(fmt_currency)

            st.markdown("#### Cheapest visible offer by length")
            st.dataframe(cheapest_by_length, use_container_width=True, hide_index=True)

# -----------------------------
# Tab 2: All price points
# -----------------------------
with tab2:
    st.subheader("All visible price points by competitor")
    st.caption("Shows every visible monthly price point. NordVPN stays blue across charts.")

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
                    "scale": COMPETITOR_COLOR_SCALE,
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
    st.subheader("Competitor comparison")
    st.caption("Simple range view without median or hard-to-read columns.")

    comparison = (
        filtered.sort_values(["Competitor", "Price per month", "Date"])
        .groupby("Competitor", as_index=False)
        .agg(
            Lowest_visible_monthly_price=("Price per month", "min"),
            Highest_visible_monthly_price=("Price per month", "max"),
            Latest_visible_scrape=("Date", "max"),
        )
        .sort_values("Lowest_visible_monthly_price")
    )

    comparison["Lowest_visible_monthly_price"] = comparison["Lowest_visible_monthly_price"].map(fmt_currency)
    comparison["Highest_visible_monthly_price"] = comparison["Highest_visible_monthly_price"].map(fmt_currency)

    st.dataframe(comparison, use_container_width=True, hide_index=True)

# -----------------------------
# Tab 4: Trend lines
# -----------------------------
with tab4:
    st.subheader("Pricing trend lines over time")
    st.caption("Use current filters first. Then choose which visible lines to show.")

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
                title_color = "#4285f4" if comp == "NordVPN" else "#111111"
                st.markdown(
                    f"<div style='font-size:1.05rem;font-weight:600;color:{title_color};margin-top:10px'>{comp}</div>",
                    unsafe_allow_html=True,
                )
                st.caption("Showing the currently visible plans for this competitor.")

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
                        "height": 320,
                    },
                    use_container_width=True,
                )

# -----------------------------
# Tab 5: Timeline
# -----------------------------
with tab5:
    st.subheader("All visible price points over time")
    st.caption("Every visible scrape date plotted as a point.")

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
                    "color": {
                        "field": "Competitor",
                        "type": "nominal",
                        "scale": COMPETITOR_COLOR_SCALE,
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
# Tab 6: Event view
# -----------------------------
with tab6:
    st.subheader("Price points by event")
    st.caption("For each predefined event, this shows the cheapest 2-year plan per competitor. Plan lengths considered: 24, 27, 28 months.")

    event_source = filtered.copy()
    event_source = event_source.dropna(subset=["Date", "Price per month"])

    if "Length (in months)" in event_source.columns:
        event_source = event_source[
            event_source["Length (in months)"].fillna(-1).astype(int).isin(TWO_YEAR_LENGTHS)
        ]

    if event_source.empty:
        st.warning("No visible rows available for 2-year plans (24, 27, 28 months) under current filters.")
    else:
        event_rows = []

        for event_name, event_date_str in EVENTS.items():
            target_date = pd.to_datetime(event_date_str)
            df_event = event_source.copy()
            df_event["date_diff"] = (df_event["Date"] - target_date).abs()

            closest_dates = (
                df_event.groupby("Competitor", as_index=False)["date_diff"]
                .min()
                .rename(columns={"date_diff": "min_diff"})
            )

            df_event = df_event.merge(closest_dates, on="Competitor", how="inner")
            df_event = df_event[df_event["date_diff"] == df_event["min_diff"]].copy()

            cheapest_per_competitor = (
                df_event.sort_values(["Competitor", "Price per month", "Total price"])
                .groupby("Competitor", as_index=False)
                .first()
            )

            cheapest_per_competitor["Event"] = event_name
            cheapest_per_competitor["Target event date"] = target_date
            event_rows.append(cheapest_per_competitor)

        if not event_rows:
            st.warning("No event rows could be built from the current filters.")
        else:
            event_df = pd.concat(event_rows, ignore_index=True)

            st.markdown("#### Cheapest 2Y plan by event")
            st.caption("Green text below the chart explains what this view contains.")

            st.vega_lite_chart(
                event_df,
                {
                    "mark": {"type": "line", "point": True},
                    "encoding": {
                        "x": {
                            "field": "Event",
                            "type": "ordinal",
                            "sort": list(EVENTS.keys()),
                            "title": "Event",
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
                            "scale": COMPETITOR_COLOR_SCALE,
                        },
                        "tooltip": [
                            {"field": "Event", "type": "nominal"},
                            {"field": "Competitor", "type": "nominal"},
                            {"field": "Plan name", "type": "nominal"},
                            {"field": "Type", "type": "nominal"},
                            {"field": "Length (in months)", "type": "quantitative"},
                            {"field": "Price per month", "type": "quantitative", "format": "$.2f"},
                            {"field": "Total price", "type": "quantitative", "format": "$.2f"},
                            {"field": "Date", "type": "temporal", "format": "%Y-%m-%d"},
                        ],
                    },
                    "height": 450,
                },
                use_container_width=True,
            )

            st.markdown(
                "<div style='font-size:0.85rem;color:#188038;margin-top:6px'>"
                "This chart uses the closest scrape date to each predefined event date, "
                "then chooses the cheapest visible 24/27/28-month plan for each competitor."
                "</div>",
                unsafe_allow_html=True,
            )

            st.markdown("#### Event comparison table")
            st.caption("This table shows which plan was chosen for each competitor at each event.")

            event_table = event_df[
                [
                    "Event",
                    "Competitor",
                    "Plan name",
                    "Type",
                    "Length (in months)",
                    "Price per month",
                    "Total price",
                    "Date",
                ]
            ].copy()

            event_table["Price per month"] = event_table["Price per month"].map(fmt_currency)
            event_table["Total price"] = event_table["Total price"].map(fmt_currency)

            st.dataframe(
                event_table.sort_values(["Event", "Competitor"]),
                use_container_width=True,
                hide_index=True,
            )

# -----------------------------
# Tab 7: Raw data
# -----------------------------
with tab7:
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
        "that usually means the source rows in the Excel file are structured that way."
    )
