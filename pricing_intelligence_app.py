# 6. Date range filter with 2 separate calendar pickers
filtered = step_df.copy()

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
