import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from api_client import get_item_mapping
from calculator import calculate_rpi, calculate_monthly_rpi_dataframe
from config import DEFAULT_RPI_BASKET

st.set_page_config(page_title="OSRS Inflation Calculator", page_icon="📈", layout="wide")

st.title("OSRS Inflation Calculator")
st.markdown("""
Welcome! This tool calculates the inflation rate for items in Old School Runescape based on the default RPI basket.

The **Current RPI Metrics** below track short-term changes (7-day and 30-day averages) against both the previous year and the previous month.
""")

# --- Load Mapping Data ---
@st.cache_data(ttl="6h")
def load_mapping_data():
    """Helper to cache the mapping data and item list."""
    return get_item_mapping()

with st.spinner("Loading OSRS item database..."):
    mapping_dict, item_names_list = load_mapping_data()

# --- Main App Logic ---
if mapping_dict and item_names_list:

    today = datetime.now().date()

    # ------------------------------------------------
    # 1. CURRENT RPI CALCULATIONS (YoY and MoM)
    # ------------------------------------------------
    st.header("Current RPI Metrics (Default Basket)")

    # Define all periods needed for 4 metrics

    # --- YoY (30-day Average) ---
    yoy30_curr_end = today
    yoy30_curr_start = today - timedelta(days=30)
    yoy30_old_start = yoy30_curr_start - timedelta(days=365)
    yoy30_old_end = yoy30_curr_end - timedelta(days=365)

    # --- YoY (7-day Average) ---
    yoy7_curr_end = today
    yoy7_curr_start = today - timedelta(days=7)
    yoy7_old_start = yoy7_curr_start - timedelta(days=365)
    yoy7_old_end = yoy7_curr_end - timedelta(days=365)

    # --- MoM (30-day Average) ---
    mom30_curr_end = today
    mom30_curr_start = today - timedelta(days=30)
    mom30_old_start = mom30_curr_start - timedelta(days=30)
    mom30_old_end = mom30_curr_end - timedelta(days=30)

    # --- MoM (7-day Average) ---
    mom7_curr_end = today
    mom7_curr_start = today - timedelta(days=7)
    mom7_old_start = mom7_curr_start - timedelta(days=30)
    mom7_old_end = mom7_curr_end - timedelta(days=30)


    with st.spinner("Calculating current RPI figures..."):
        # Run 4 calculations
        rpi_yoy30, excluded_yoy30 = calculate_rpi(DEFAULT_RPI_BASKET, yoy30_old_start, yoy30_curr_end, mapping_dict, show_progress=False)
        rpi_yoy7, excluded_yoy7 = calculate_rpi(DEFAULT_RPI_BASKET, yoy7_old_start, yoy7_curr_end, mapping_dict, show_progress=False)
        rpi_mom30, excluded_mom30 = calculate_rpi(DEFAULT_RPI_BASKET, mom30_old_start, mom30_curr_end, mapping_dict, show_progress=False)
        rpi_mom7, excluded_mom7 = calculate_rpi(DEFAULT_RPI_BASKET, mom7_old_start, mom7_curr_end, mapping_dict, show_progress=False)


    # --- Display Current Metrics (YoY Block) ---
    st.subheader("Year-over-Year (YoY) Inflation")
    col_yoy30, col_yoy7 = st.columns(2)

    with col_yoy30:
        yoy30_label = f"YoY RPI (30-day Average)"
        if rpi_yoy30 is not None:
            st.metric(label=yoy30_label, value=f"{rpi_yoy30:.2f}%", delta_color="inverse")
        else:
            st.warning(f"Data for 30-day YoY missing.")

    with col_yoy7:
        yoy7_label = f"YoY RPI (7-day Average)"
        if rpi_yoy7 is not None:
            st.metric(label=yoy7_label, value=f"{rpi_yoy7:.2f}%", delta_color="inverse")
        else:
            st.warning(f"Data for 7-day YoY missing.")

    # --- Display Current Metrics (MoM Block) ---
    st.subheader("Month-on-Month (MoM) Inflation")
    col_mom30, col_mom7 = st.columns(2)

    with col_mom30:
        mom30_label = f"MoM RPI (30-day Average)"
        if rpi_mom30 is not None:
            st.metric(label=mom30_label, value=f"{rpi_mom30:.2f}%", delta_color="inverse")
        else:
            st.warning(f"Data for 30-day MoM missing.")

    with col_mom7:
        mom7_label = f"MoM RPI (7-day Average)"
        if rpi_mom7 is not None:
            st.metric(label=mom7_label, value=f"{rpi_mom7:.2f}%", delta_color="inverse")
        else:
            st.warning(f"Data for 7-day MoM missing.")


    # --- Display Exclusions ---
    all_excluded = set(excluded_yoy30) | set(excluded_yoy7) | set(excluded_mom30) | set(excluded_mom7)
    if all_excluded:
        st.info("Note: Some basket items were excluded from these calculations due to missing historical data.")

    st.markdown("---")


    # ------------------------------------------------
    # 2. FULL HISTORICAL RPI CHART
    # ------------------------------------------------
    st.subheader("Historical YoY RPI Trend (Full Data)")

    with st.spinner("Building historical chart from all available data..."):
        # Calculate RPI for all available history
        historical_df = calculate_monthly_rpi_dataframe(
            basket=DEFAULT_RPI_BASKET,
            mapping_dict=mapping_dict
        )

    if not historical_df.empty:
        # Render chart with a smaller height as requested
        st.line_chart(historical_df, y='YoY RPI (%)', height=300)
    else:
        st.error("Historical data could not be generated. Check API connection or data availability.")

    st.markdown("---")


    # ------------------------------------------------
    # 3. HISTORICAL DATE CALCULATOR
    # ------------------------------------------------
    st.header("Historical RPI Date Checker")
    st.markdown("Select a date in the past to see the short-term RPI calculated from that specific point in time.")

    # Use max=today to prevent future date selection
    historical_date = st.date_input(
        "Select Historical Date:",
        value=today - timedelta(days=90),
        max_value=today
    )

    if st.button("Calculate Historical Figures", type="primary"):
        # --- Define historical periods based on selected date ---

        # MoM 7-Day from historical date
        h_mom7_curr_end = historical_date
        h_mom7_curr_start = historical_date - timedelta(days=7)
        h_mom7_old_start = h_mom7_curr_start - timedelta(days=30)
        h_mom7_old_end = h_mom7_curr_end - timedelta(days=30)

        # YoY 30-Day from historical date
        h_yoy30_curr_end = historical_date
        h_yoy30_curr_start = historical_date - timedelta(days=30)
        h_yoy30_old_start = h_yoy30_curr_start - timedelta(days=365)
        h_yoy30_old_end = h_yoy30_curr_end - timedelta(days=365)

        with st.spinner(f"Calculating RPI figures relative to {historical_date}..."):

            # 1. YoY (30 days ending at historical date vs. 30 days last year)
            h_rpi_yoy30, h_excluded_yoy30 = calculate_rpi(
                DEFAULT_RPI_BASKET, h_yoy30_old_start, h_yoy30_curr_end, mapping_dict, show_progress=False
            )

            # 2. MoM (7 days ending at historical date vs. 7 days last month)
            h_rpi_mom7, h_excluded_mom7 = calculate_rpi(
                DEFAULT_RPI_BASKET, h_mom7_old_start, h_mom7_curr_end, mapping_dict, show_progress=False
            )

        # --- Display Historical Metrics ---
        st.markdown(f"### Results for period ending: {historical_date}")
        h_col1, h_col2 = st.columns(2)

        with h_col1:
            h_yoy_label = f"YoY RPI (30-day Avg: {h_yoy30_old_end} to {h_yoy30_curr_end})"
            if h_rpi_yoy30 is not None:
                st.metric(label=h_yoy_label, value=f"{h_rpi_yoy30:.2f}%", delta_color="inverse")
            else:
                st.warning(f"Could not calculate {h_yoy_label}. Data missing.")

        with h_col2:
            h_mom_label = f"MoM RPI (7-day Avg: {h_mom7_old_end} to {h_mom7_curr_end})"
            if h_rpi_mom7 is not None:
                st.metric(label=h_mom_label, value=f"{h_rpi_mom7:.2f}%", delta_color="inverse")
            else:
                st.warning(f"Could not calculate {h_mom_label}. Data missing.")

        if h_excluded_yoy30 or h_excluded_mom7:
             all_excluded = set(h_excluded_yoy30) | set(h_excluded_mom7)
             if all_excluded:
                st.info(f"Note: {len(all_excluded)} item(s) excluded from these historical calculations due to missing data.")


else:
    st.error("Failed to load OSRS item database. The API might be down. Please try again later.")
