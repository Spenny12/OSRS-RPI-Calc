import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from api_client import get_item_mapping
from calculator import calculate_rpi, calculate_monthly_rpi_dataframe
from config import DEFAULT_RPI_BASKET

st.set_page_config(page_title="OSRS Inflation Calculator", page_icon="📈", layout="wide")

st.title("OSRS Inflation Calculator")

st.markdown("""
Welcome! This tool calculates the inflation rate for items in Old School Runescape.

The **OSRS RPI** below is a weighted inflation rate based on a default basket of 86 popular items.
The metrics are calculated using average high prices from the period specified.

Use the **Custom Calculator** page in the sidebar to build your own basket or analyze a single item.
""")

# --- Load Mapping Data ---
with st.spinner("Loading OSRS item database... (This is only done once)"):
    mapping_dict, item_names_list = get_item_mapping()

# --- Main App Logic ---
if not mapping_dict or not item_names_list:
    st.error("Failed to load OSRS item database. The API might be down. Please try again later.")
    st.stop()


# --- Current RPI Figures ---
st.header("1. Current OSRS RPI Metrics")
today = datetime.now().date()

# Define dates anchored to the 1st of the month for consistency with the historical graph.
# This avoids discrepancies caused by daily market fluctuations.

# Current period end (1st of the current month)
current_month_start = date(today.year, today.month, 1)

# Previous month start (1st of the previous month)
if current_month_start.month == 1:
    prev_month_start = date(current_month_start.year - 1, 12, 1)
else:
    prev_month_start = date(current_month_start.year, current_month_start.month - 1, 1)

# Previous year start (1st of the current month, one year prior)
prev_year_start = current_month_start.replace(year=current_month_start.year - 1)


# FIX: Simplify the function to only perform the necessary RPI calculation.
def calculate_metric(name, start_date, end_date):
    """Calculates RPI for a given comparison period and returns results/exclusions."""

    # Calculate RPI from start_date to end_date (The actual metric)
    rpi_final, excluded_final = calculate_rpi(
        DEFAULT_RPI_BASKET, start_date, end_date, mapping_dict, show_progress=False
    )

    return rpi_final, excluded_final

all_metrics = []
all_exclusions = {}

with st.spinner("Calculating current RPI metrics..."):

    # Redefine metrics to use the consistent 1st-of-the-month dates.

    # YoY (Monthly): 1st of Year-1 vs 1st of Current Year
    yoy_monthly_start = prev_year_start
    yoy_monthly_end = current_month_start
    rpi_yoy_monthly, exc_yoy_monthly = calculate_metric("YoY (Monthly RPI)", yoy_monthly_start, yoy_monthly_end)
    all_metrics.append(("YoY (Monthly RPI)", rpi_yoy_monthly, yoy_monthly_start, yoy_monthly_end))
    all_exclusions["YoY (Monthly RPI)"] = exc_yoy_monthly

    # MoM (Monthly): 1st of Previous Month vs 1st of Current Month
    mom_monthly_start = prev_month_start
    mom_monthly_end = current_month_start
    rpi_mom_monthly, exc_mom_monthly = calculate_metric("MoM (Monthly RPI)", mom_monthly_start, mom_monthly_end)
    all_metrics.append(("MoM (Monthly RPI)", rpi_mom_monthly, mom_monthly_start, mom_monthly_end))
    all_exclusions["MoM (Monthly RPI)"] = exc_mom_monthly

    # Retaining the 7-Day and 30-Day metrics, but now they are calculated using today's specific date.

    # YoY (30-day): 30 days ago, one year prior vs 30 days ago, today
    yoy_30_end = today - timedelta(days=30)
    yoy_30_compare_end = yoy_30_end.replace(year=yoy_30_end.year - 1)
    rpi_yoy_30, exc_yoy_30 = calculate_metric("YoY (30-Day Avg)", yoy_30_compare_end, yoy_30_end)
    all_metrics.append(("YoY (30-Day Avg)", rpi_yoy_30, yoy_30_compare_end, yoy_30_end))
    all_exclusions["YoY (30-Day Avg)"] = exc_yoy_30

    # YoY (7-day): 7 days ago, one year prior vs 7 days ago, today
    yoy_7_end = today - timedelta(days=7)
    yoy_7_compare_end = yoy_7_end.replace(year=yoy_7_end.year - 1)
    rpi_yoy_7, exc_yoy_7 = calculate_metric("YoY (7-Day Avg)", yoy_7_compare_end, yoy_7_end)
    all_metrics.append(("YoY (7-Day Avg)", rpi_yoy_7, yoy_7_compare_end, yoy_7_end))
    all_exclusions["YoY (7-Day Avg)"] = exc_yoy_7

    # MoM (30-day): 30 days ago, one month prior vs 30 days ago, today
    mom_30_end = today - timedelta(days=30)
    mom_30_compare_end = mom_30_end - timedelta(days=30)
    rpi_mom_30, exc_mom_30 = calculate_metric("MoM (30-Day Avg)", mom_30_compare_end, mom_30_end)
    all_metrics.append(("MoM (30-Day Avg)", rpi_mom_30, mom_30_compare_end, mom_30_end))
    all_exclusions["MoM (30-Day Avg)"] = exc_mom_30

    # MoM (7-day): 7 days ago, one month prior vs 7 days ago, today
    mom_7_end = today - timedelta(days=7)
    mom_7_compare_end = mom_7_end - timedelta(days=30)
    rpi_mom_7, exc_mom_7 = calculate_metric("MoM (7-Day Avg)", mom_7_compare_end, mom_7_end)
    all_metrics.append(("MoM (7-Day Avg)", rpi_mom_7, mom_7_compare_end, mom_7_end))
    all_exclusions["MoM (7-Day Avg)"] = exc_mom_7


# Display current RPI figures
col_yoy, col_mom = st.columns(2)

with col_yoy:
    st.subheader("Year-over-Year Inflation (YoY)")
    # Show Monthly RPI first, then the 30-day/7-day points
    for label, value, start, end in all_metrics[:4]:
        if "YoY" in label:
            st.metric(
                label=f"{label} ({start} to {end})",
                value=f"{value:.2f}%" if value is not None else "N/A"
            )

with col_mom:
    st.subheader("Month-over-Month Inflation (MoM)")
    # Show Monthly RPI first, then the 30-day/7-day points
    for label, value, start, end in all_metrics[:4]:
        if "MoM" in label:
            st.metric(
                label=f"{label} ({start} to {end})",
                value=f"{value:.2f}%" if value is not None else "N/A"
            )

# ... (rest of the file remains the same)
# Display exclusions in a dedicated section
all_excluded = [item for sublist in all_exclusions.values() for item in sublist]
if all_excluded:
    with st.expander("⚠️ Items Excluded from Calculations"):
        for metric, exclusions in all_exclusions.items():
            if exclusions:
                st.markdown(f"**{metric}:**")
                for item in exclusions:
                    st.markdown(f"- {item}")
        st.markdown("""
        *Note: An item is excluded from a specific metric if it was not available or lacks price data during the start or end period of that calculation.*
        """)


# --- Historical RPI Chart ---
st.header("2. Historical OSRS RPI Trend")
with st.spinner("Generating full historical chart (This is cached)..."):
    history_df = calculate_monthly_rpi_dataframe(DEFAULT_RPI_BASKET, mapping_dict)

if history_df is not None and not history_df.empty:
    st.line_chart(
        history_df,
        y="YoY RPI (%)",
        height=300 # Making the chart smaller as requested
    )
    st.markdown("---")
else:
    st.warning("Could not generate historical RPI chart data.")


# --- Historical Date Checker ---
st.header("3. Calculate Historical Figures")
st.markdown("Use this tool to calculate the 7-day MoM and 30-day YoY RPI relative to a past date.")

historical_date = st.date_input("Select Historical Anchor Date", value=today - timedelta(days=365))

if st.button("Calculate Historical Metrics", type="secondary"):

    # Calculate MoM (7-day) relative to historical date
    h_mom_7_end = historical_date
    h_mom_7_compare_end = h_mom_7_end - timedelta(days=30)

    h_rpi_mom_7, h_exc_mom_7 = calculate_rpi(
        DEFAULT_RPI_BASKET, h_mom_7_compare_end, h_mom_7_end, mapping_dict, show_progress=True
    )

    # Calculate YoY (30-day) relative to historical date
    h_yoy_30_end = historical_date
    h_yoy_30_compare_end = h_yoy_30_end - timedelta(days=365)

    h_rpi_yoy_30, h_exc_yoy_30 = calculate_rpi(
        DEFAULT_RPI_BASKET, h_yoy_30_compare_end, h_yoy_30_end, mapping_dict, show_progress=True
    )

    st.subheader(f"Results Relative to {historical_date}:")

    h_col1, h_col2 = st.columns(2)

    with h_col1:
        st.metric(
            label=f"30-Day YoY Inflation ({h_yoy_30_compare_end} to {h_yoy_30_end})",
            value=f"{h_rpi_yoy_30:.2f}%" if h_rpi_yoy_30 is not None else "N/A"
        )

    with h_col2:
        st.metric(
            label=f"7-Day MoM Inflation ({h_mom_7_compare_end} to {h_mom_7_end})",
            value=f"{h_rpi_mom_7:.2f}%" if h_rpi_mom_7 is not None else "N/A"
        )

    # Historical Exclusions
    all_h_excluded = list(set(h_exc_mom_7 + h_exc_yoy_30))
    if all_h_excluded:
        with st.expander("⚠️ Items Excluded from Historical Calculation"):
            st.markdown("The following items lacked price data for one or both comparison periods:")
            for item in all_h_excluded:
                st.markdown(f"- {item}")
