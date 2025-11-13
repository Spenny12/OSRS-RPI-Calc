import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from api_client import get_item_mapping
from calculator import calculate_rpi, calculate_monthly_rpi_dataframe
from config import DEFAULT_RPI_BASKET

st.set_page_config(page_title="OSRS Inflation Calculator", page_icon="📈", layout="wide")

st.title("OSRS Inflation Calculator")

st.markdown("""
Welcome! This tool calculates the inflation rate for items in Old School Runescape.

The **Current RPI** figures below are based on a default basket of popular items.
The new **Historical Chart** shows the Year-over-Year (YoY) RPI for the last two years.

Use the **"Custom Calculator"** page in the sidebar to build your own basket or analyze single items.
""")

# --- Load Mapping Data ---
# Use a spinner for good user experience
with st.spinner("Loading OSRS item database..."):
    mapping_dict, item_names_list = get_item_mapping()

# --- Main App Logic ---
if mapping_dict and item_names_list:

    today = datetime.now().date()

    # ------------------------------------------------
    # 1. CURRENT RPI CALCULATIONS (MoM & YoY)
    # ------------------------------------------------
    st.header("Current RPI Figures (Default Basket)")

    # YoY 30-Day: Compare last 30 days vs. 30 days same period last year
    yoy_current_end = today
    yoy_current_start = today - timedelta(days=30)
    yoy_old_start = yoy_current_start - timedelta(days=365)
    yoy_old_end = yoy_current_end - timedelta(days=365)

    # MoM 7-Day: Compare last 7 days vs. 7 days same period last month
    mom_current_end = today
    mom_current_start = today - timedelta(days=7)
    mom_old_start = mom_current_start - timedelta(days=30)
    mom_old_end = mom_current_end - timedelta(days=30)

    with st.spinner("Calculating current RPI figures..."):
        # 1. YoY (Current 30 days vs. 30 days last year)
        # Calculates inflation between the 30 days starting yoy_old_start and the 30 days starting yoy_current_start
        rpi_yoy_current, _ = calculate_rpi(
            DEFAULT_RPI_BASKET, yoy_old_start, yoy_current_end, mapping_dict, show_progress=False
        )

        # 2. MoM (Current 7 days vs. 7 days last month)
        # Calculates inflation between the 7 days starting mom_old_start and the 7 days starting mom_current_start
        rpi_mom_current, excluded_mom_curr = calculate_rpi(
            DEFAULT_RPI_BASKET, mom_old_start, mom_current_end, mapping_dict, show_progress=False
        )

    # --- Display Current Metrics ---
    col1, col2 = st.columns(2)

    with col1:
        yoy_label = f"YoY RPI ({yoy_old_end} to {yoy_current_end})"
        if rpi_yoy_current is not None:
            st.metric(label=yoy_label, value=f"{rpi_yoy_current:.2f}%")
        else:
            st.warning(f"Could not calculate {yoy_label}. Data missing.")

    with col2:
        mom_label = f"MoM RPI ({mom_old_end} to {mom_current_end})"
        if rpi_mom_current is not None:
            st.metric(label=mom_label, value=f"{rpi_mom_current:.2f}%")
        else:
            st.warning(f"Could not calculate {mom_label}. Data missing.")


    # ------------------------------------------------
    # 2. MONTHLY HISTORICAL RPI CHART (Last 24 Months)
    # ------------------------------------------------
    st.subheader("Monthly YoY RPI Trend (Last 24 Months)")

    with st.spinner("Building 24-month historical chart..."):
        historical_df = calculate_monthly_rpi_dataframe(
            basket=DEFAULT_RPI_BASKET,
            num_months=24,
            mapping_dict=mapping_dict
        )

    if not historical_df.empty:
        # Streamlit's line_chart uses the index as the x-axis automatically
        st.line_chart(historical_df, y='YoY RPI (%)')
    else:
        st.error("Historical data could not be generated. Check API connection or data availability.")

    st.markdown("---")


    # ------------------------------------------------
    # 3. HISTORICAL DATE CALCULATOR
    # ------------------------------------------------
    st.header("Historical RPI Date Checker")
    st.markdown("Select a date in the past to see the 7-day MoM and 30-day YoY RPI calculated from that specific point in time.")

    # Use max=today to prevent future date selection
    historical_date = st.date_input(
        "Select Historical Date:",
        value=today - timedelta(days=90),
        max_value=today
    )

    if st.button("Calculate Historical Figures", type="primary"):
        # --- Define historical periods based on selected date ---

        # MoM 7-Day from historical date
        h_mom_current_end = historical_date
        h_mom_current_start = historical_date - timedelta(days=7)
        h_mom_old_start = h_mom_current_start - timedelta(days=30)
        h_mom_old_end = h_mom_current_end - timedelta(days=30)

        # YoY 30-Day from historical date
        h_yoy_current_end = historical_date
        h_yoy_current_start = historical_date - timedelta(days=30)
        h_yoy_old_start = h_yoy_current_start - timedelta(days=365)
        h_yoy_old_end = h_yoy_current_end - timedelta(days=365)

        with st.spinner(f"Calculating RPI figures relative to {historical_date}..."):

            # 1. YoY (30 days ending at historical date vs. 30 days last year)
            h_rpi_yoy, h_excluded_yoy = calculate_rpi(
                DEFAULT_RPI_BASKET, h_yoy_old_start, h_yoy_current_end, mapping_dict, show_progress=False
            )

            # 2. MoM (7 days ending at historical date vs. 7 days last month)
            h_rpi_mom, h_excluded_mom = calculate_rpi(
                DEFAULT_RPI_BASKET, h_mom_old_start, h_mom_current_end, mapping_dict, show_progress=False
            )

        # --- Display Historical Metrics ---
        h_col1, h_col2 = st.columns(2)

        with h_col1:
            h_yoy_label = f"YoY RPI ({h_yoy_old_end} to {h_yoy_current_end})"
            if h_rpi_yoy is not None:
                st.metric(label=h_yoy_label, value=f"{h_rpi_yoy:.2f}%")
            else:
                st.warning(f"Could not calculate {h_yoy_label}. Data missing.")

        with h_col2:
            h_mom_label = f"MoM RPI ({h_mom_old_end} to {h_mom_current_end})"
            if h_rpi_mom is not None:
                st.metric(label=h_mom_label, value=f"{h_rpi_mom:.2f}%")
            else:
                st.warning(f"Could not calculate {h_mom_label}. Data missing.")

        if h_excluded_yoy or h_excluded_mom:
             all_excluded = set(h_excluded_yoy) | set(h_excluded_mom)
             if all_excluded:
                st.warning(f"Note: Some items were excluded from these historical calculations due to missing data:")
                for item in sorted(list(all_excluded)):
                    st.markdown(f"- {item}")


else:
    st.error("Failed to load OSRS item database. The API might be down. Please try again later.")
