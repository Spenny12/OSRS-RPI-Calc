import streamlit as st
from datetime import datetime, timedelta
from api_client import get_item_mapping
from calculator import calculate_rpi
from config import DEFAULT_RPI_BASKET

st.set_page_config(page_title="OSRS Inflation Calculator", page_icon="📈", layout="wide")

st.title("OSRS Inflation Calculator")

st.markdown("""
Hi Kier

The "OSRS RPI" displayed below compares weighted inflation rates over different periods
based on a default basket of popular items.

Use the **"Custom Calculator"** page in the sidebar to:
- Calculate inflation for any single item.
- Build your own custom RPI basket.
- Select custom date ranges.
""")

st.header(f"Default OSRS 'RPI' Figures")

# --- Load Mapping Data ---
# Use a spinner for good user experience
with st.spinner("Loading OSRS item database..."):
    mapping_dict, item_names_list = get_item_mapping()

# --- Main App Logic ---
if mapping_dict and item_names_list:
    # --- Define all 8 dates for the calculations ---
    today = datetime.now().date()

    # YoY Dates: (Last 30 days) vs (Same 30 days, 1 year ago)
    yoy_current_start = today - timedelta(days=30)
    yoy_current_end = today
    yoy_prev_year_start = today - timedelta(days=365 + 30)
    yoy_prev_year_end = today - timedelta(days=365)

    # MoM Dates: (Last 7 days) vs (Same 7 days, 1 month ago)
    mom_current_start = today - timedelta(days=7)
    mom_current_end = today
    mom_prev_month_start = today - timedelta(days=30 + 7)
    mom_prev_month_end = today - timedelta(days=30)

    # --- Run all 4 calculations ---
    with st.spinner("Calculating RPI figures for YoY and MoM..."):
        # Run YoY calcs (silently)
        rpi_yoy_current, excluded_yoy_curr = calculate_rpi(
            DEFAULT_RPI_BASKET, yoy_current_start, yoy_current_end, mapping_dict, show_progress=False
        )
        rpi_yoy_prev, excluded_yoy_prev = calculate_rpi(
            DEFAULT_RPI_BASKET, yoy_prev_year_start, yoy_prev_year_end, mapping_dict, show_progress=False
        )

        # Run MoM calcs (silently)
        rpi_mom_current, excluded_mom_curr = calculate_rpi(
            DEFAULT_RPI_BASKET, mom_current_start, mom_current_end, mapping_dict, show_progress=False
        )
        rpi_mom_prev, excluded_mom_prev = calculate_rpi(
            DEFAULT_RPI_BASKET, mom_prev_month_start, mom_prev_month_end, mapping_dict, show_progress=False
        )

    # --- Display Results in Columns ---
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Year-over-Year Inflation")
        st.markdown(f"Compares 30-day inflation from `{yoy_current_start}` to `{yoy_current_end}` vs. the same period last year.")

        if rpi_yoy_current is not None:
            # Calculate delta if previous data exists
            delta_yoy = f"{rpi_yoy_current - rpi_yoy_prev:.2f} pt change" if rpi_yoy_prev is not None else None
            st.metric(
                label="Current 30-Day RPI",
                value=f"{rpi_yoy_current:.2f}%",
                delta=delta_yoy
            )
        else:
            st.error("Could not calculate current 30-day RPI.")

        if rpi_yoy_prev is not None:
            st.metric(
                label=f"Prior Year 30-Day RPI ({yoy_prev_year_end})",
                value=f"{rpi_yoy_prev:.2f}%"
            )
        else:
            st.warning("No RPI data for the prior year period.")

    with col2:
        st.subheader("Month-over-Month Inflation")
        st.markdown(f"Compares 7-day inflation from `{mom_current_start}` to `{mom_current_end}` vs. the same period last month.")

        if rpi_mom_current is not None:
            # Calculate delta if previous data exists
            delta_mom = f"{rpi_mom_current - rpi_mom_prev:.2f} pt change" if rpi_mom_prev is not None else None
            st.metric(
                label="Current 7-Day RPI",
                value=f"{rpi_mom_current:.2f}%",
                delta=delta_mom
            )
        else:
            st.error("Could not calculate current 7-day RPI.")

        if rpi_mom_prev is not None:
            st.metric(
                label=f"Prior Month 7-Day RPI ({mom_prev_month_end})",
                value=f"{rpi_mom_prev:.2f}%"
            )
        else:
            st.warning("No RPI data for the prior month period.")

    # --- Show excluded items (collated from all runs) ---
    all_excluded = set(excluded_yoy_curr + excluded_yoy_prev + excluded_mom_curr + excluded_mom_prev)
    if all_excluded:
        with st.expander("View items excluded from calculations"):
            st.warning("Some items were excluded from one or more calculations (e.g., ID not found, no price data for a period).")
            for item in all_excluded:
                st.markdown(f"- {item}")

    st.subheader("Default Basket Definition")
    st.json({k: f"{v*100:.0f}%" for k, v in DEFAULT_RPI_BASKET.items()})

else:
    st.error("Failed to load OSRS item database. The API might be down. Please try again later.")
