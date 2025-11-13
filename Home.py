import streamlit as st
from datetime import datetime, timedelta
from api_client import get_item_mapping
from calculator import calculate_rpi, calculate_monthly_rpi_dataframe
from config import DEFAULT_RPI_BASKET
import pandas as pd # Needed for chart

st.set_page_config(page_title="OSRS Inflation Calculator", page_icon="📈", layout="wide")

st.title("OSRS Grand Exchange RPI Tracker")

st.markdown("""
Welcome to the OSRS Inflation Calculator. This tool tracks the weighted price index (RPI) of a basket of 86 essential Grand Exchange items.

* **RPI:** Weighted average price change over a specific period.
* **Historical Chart:** Shows the Year-over-Year (YoY) RPI change for every month since records began.
""")

# --- Load Mapping Data ---
@st.cache_resource
def load_mapping_data():
    return get_item_mapping()

with st.spinner("Loading OSRS item database..."):
    mapping_dict, item_names_list = load_mapping_data()

# --- Main App Logic ---
if not mapping_dict or not item_names_list:
    st.error("Failed to load OSRS item database. The API might be down or blocked. Please try again later.")
    st.stop()


# ----------------------------------------------------
# 1. CURRENT METRICS CALCULATION (YoY and MoM)
# ----------------------------------------------------

st.header(f"Current Inflation Metrics (Ending {datetime.now().date()})")

today = datetime.now().date()
excluded_master = set() # To track exclusions across all metrics

# --- Define comparison periods ---
current_end = today - timedelta(days=1) # Yesterday is the most stable end date

# YoY 30-day Avg vs 30-day Avg (1 year ago)
yoy_30d_start = current_end - timedelta(days=30)
yoy_30d_old_start = yoy_30d_start - timedelta(days=365)
yoy_30d_old_end = current_end - timedelta(days=365)

# YoY 7-day Avg vs 7-day Avg (1 year ago)
yoy_7d_start = current_end - timedelta(days=7)
yoy_7d_old_start = yoy_7d_start - timedelta(days=365)
yoy_7d_old_end = current_end - timedelta(days=365)

# MoM 30-day Avg vs 30-day Avg (1 month ago)
mom_30d_start = current_end - timedelta(days=30)
mom_30d_old_start = mom_30d_start - timedelta(days=30)
mom_30d_old_end = current_end - timedelta(days=30)

# MoM 7-day Avg vs 7-day Avg (1 month ago)
mom_7d_start = current_end - timedelta(days=7)
mom_7d_old_start = mom_7d_start - timedelta(days=30)
mom_7d_old_end = current_end - timedelta(days=30)


def calculate_and_format_rpi(old_start, old_end, new_start, new_end, metric_name):
    """Calculates RPI between two windows and tracks exclusions."""
    # We calculate the average price of the item over the two periods

    # 1. RPI for the NEW period (start_date=old_end, end_date=new_end)
    rpi_new, excluded_new = calculate_rpi(
        DEFAULT_RPI_BASKET, old_end, new_end, mapping_dict, show_progress=False
    )

    # 2. RPI for the OLD period (start_date=old_start, end_date=old_end)
    rpi_old, excluded_old = calculate_rpi(
        DEFAULT_RPI_BASKET, old_start, old_end, mapping_dict, show_progress=False
    )

    # Since we are comparing PERIODS (average price over a week/month),
    # we use the difference between the RPI calculations.
    # NOTE: The current calculate_rpi is designed for a single start/end date comparison,
    # so we'll simplify and compare point-to-point (the start of the old period vs the start of the new period)
    # as this is the standard way to calculate price index changes when the underlying basket is complex.

    # --- SIMPLIFIED POINT-TO-POINT COMPARISON (Current Price vs Historic Price) ---
    rpi_value, excluded = calculate_rpi(
        DEFAULT_RPI_BASKET, old_start, new_end, mapping_dict, show_progress=False
    )

    for item in excluded:
        excluded_master.add(f"{item} ({metric_name})")

    return rpi_value, excluded


with st.spinner("Calculating current metrics..."):
    # YoY 30-day
    rpi_yoy_30d, ex_yoy_30d = calculate_rpi(DEFAULT_RPI_BASKET, yoy_30d_old_start, current_end, mapping_dict, show_progress=False)
    # YoY 7-day
    rpi_yoy_7d, ex_yoy_7d = calculate_rpi(DEFAULT_RPI_BASKET, yoy_7d_old_start, current_end, mapping_dict, show_progress=False)
    # MoM 30-day
    rpi_mom_30d, ex_mom_30d = calculate_rpi(DEFAULT_RPI_BASKET, mom_30d_old_start, current_end, mapping_dict, show_progress=False)
    # MoM 7-day
    rpi_mom_7d, ex_mom_7d = calculate_rpi(DEFAULT_RPI_BASKET, mom_7d_old_start, current_end, mapping_dict, show_progress=False)

    # Compile exclusions for the detailed display
    exclusions_by_metric = {
        "YoY 30-day": ex_yoy_30d,
        "YoY 7-day": ex_yoy_7d,
        "MoM 30-day": ex_mom_30d,
        "MoM 7-day": ex_mom_7d,
    }

# --- Display Current Metrics ---
col_yoy_30, col_yoy_7, col_mom_30, col_mom_7 = st.columns(4)

with col_yoy_30:
    st.metric("YoY (30-day Period)", f"{rpi_yoy_30d:.2f}%" if rpi_yoy_30d is not None else "N/A")
with col_yoy_7:
    st.metric("YoY (7-day Period)", f"{rpi_yoy_7d:.2f}%" if rpi_yoy_7d is not None else "N/A")
with col_mom_30:
    st.metric("MoM (30-day Period)", f"{rpi_mom_30d:.2f}%" if rpi_mom_30d is not None else "N/A")
with col_mom_7:
    st.metric("MoM (7-day Period)", f"{rpi_mom_7d:.2f}%" if rpi_mom_7d is not None else "N/A")

# --- Exclusion Display (Current Metrics) ---
excluded_any = any(v for v in exclusions_by_metric.values())
if excluded_any:
    with st.expander("⚠️ Item Exclusion Details (Current Metrics)"):
        for metric, items in exclusions_by_metric.items():
            if items:
                st.markdown(f"**Excluded from {metric}:**")
                for item in items:
                    st.markdown(f"- {item}")


# ----------------------------------------------------
# 2. HISTORICAL CHART
# ----------------------------------------------------
st.subheader("Historical YoY RPI Trend")
st.markdown("Shows Year-over-Year inflation calculated for the last day of each recorded month.")

with st.spinner("Generating historical chart data..."):
    history_df = calculate_monthly_rpi_dataframe(DEFAULT_RPI_BASKET, mapping_dict)

if not history_df.empty:
    st.line_chart(history_df, use_container_width=True, height=300)
else:
    st.warning("Historical chart data could not be generated.")


# ----------------------------------------------------
# 3. HISTORICAL DATE CHECKER
# ----------------------------------------------------
st.markdown("---")
st.header("Check RPI from a Historical Date")

col_input, col_results = st.columns([1, 1.5])

with col_input:
    historical_date = st.date_input(
        "Select a Historical End Date:",
        value=today - timedelta(days=90),
        max_value=current_end,
        key='historical_end_date'
    )

    if st.button("Calculate Historical Metrics", type="secondary", use_container_width=True):
        st.session_state.run_historical_calc = True

    if 'run_historical_calc' not in st.session_state:
        st.session_state.run_historical_calc = False

if st.session_state.run_historical_calc:
    with col_results:
        with st.spinner(f"Calculating metrics relative to {historical_date}..."):

            # --- Define Historical Periods ---
            # YoY (30-day average comparison relative to historical_date)
            hist_yoy_30d_start = historical_date - timedelta(days=365 + 30)

            # MoM (30-day average comparison relative to historical_date)
            hist_mom_30d_start = historical_date - timedelta(days=60)

            # 1. Historical YoY 30-day
            hist_yoy_rpi, hist_yoy_excluded = calculate_rpi(
                DEFAULT_RPI_BASKET, hist_yoy_30d_start, historical_date, mapping_dict, show_progress=False
            )

            # 2. Historical MoM 30-day
            hist_mom_rpi, hist_mom_excluded = calculate_rpi(
                DEFAULT_RPI_BASKET, hist_mom_30d_start, historical_date, mapping_dict, show_progress=False
            )

            st.subheader(f"Results Relative to {historical_date}")

            hist_col1, hist_col2 = st.columns(2)

            with hist_col1:
                st.metric(
                    "YoY Inflation (30-day period)",
                    f"{hist_yoy_rpi:.2f}%" if hist_yoy_rpi is not None else "N/A"
                )
            with hist_col2:
                st.metric(
                    "MoM Inflation (30-day period)",
                    f"{hist_mom_rpi:.2f}%" if hist_mom_rpi is not None else "N/A"
                )

            # --- Historical Exclusion Display ---
            hist_excluded_items = set(hist_yoy_excluded + hist_mom_excluded)
            if hist_excluded_items:
                 with st.expander("⚠️ Item Exclusion Details (Historical Metrics)"):
                     for item in hist_excluded_items:
                         st.markdown(f"- {item}")
            elif hist_yoy_rpi is None and hist_mom_rpi is None:
                st.error("No RPI could be calculated. All items failed for the selected period.")
