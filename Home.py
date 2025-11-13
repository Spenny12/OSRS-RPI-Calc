import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from api_client import get_item_mapping
from calculator import calculate_rpi, calculate_monthly_rpi_dataframe, calculate_rpi_period_average
from config import DEFAULT_RPI_BASKET

st.set_page_config(page_title="OSRS Inflation Calculator", page_icon="📈", layout="wide")

st.title("OSRS Inflation Calculator")

st.markdown("""
Welcome! This is the Lil Chungies inflation calculator, created by Mod Kieren and Mod Spenny!

The **OSRS RPI** below is a weighted inflation rate based on a default basket of a load of popular items.
The metrics are calculated using average high prices from the period specified.

Use the **Custom Calculator** page in the sidebar to build your own basket or analyse a single item. No skibidi toilet!
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

# Helper to get the first day of the month
def get_first_day_of_month(d):
    return date(d.year, d.month, 1)

# Helper to get the last day of the previous month
def get_last_day_of_previous_month(d):
    first_day_of_current = get_first_day_of_month(d)
    return first_day_of_current - timedelta(days=1)

# Helper to get the 1st of the previous month
def get_first_day_of_previous_month(d):
    first_day_of_current = get_first_day_of_month(d)
    last_day_of_previous = first_day_of_current - timedelta(days=1)
    return get_first_day_of_month(last_day_of_previous)


# --- Define the four required periods ---

# 1. 7-day YoY Inflation (Today - 7 days vs 1 Year Ago - 7 days)
# Compares the price 7 days ago, one year prior, to the price 7 days ago, today. (POINT-IN-TIME)
yoy_7_day_end = today - timedelta(days=7)
yoy_7_day_start = yoy_7_day_end.replace(year=yoy_7_day_end.year - 1)

# 2. 30-day YoY Inflation (Today - 30 days vs 1 Year Ago - 30 days)
# Compares the price 30 days ago, one year prior, to the price 30 days ago, today. (POINT-IN-TIME)
yoy_30_day_end = today - timedelta(days=30)
yoy_30_day_start = yoy_30_day_end.replace(year=yoy_30_day_end.year - 1)


# 3. Weekly Figure (7-Day MoM Inflation)
# Compares price 7 days ago vs price today. (POINT-IN-TIME)
weekly_end = today
weekly_start = today - timedelta(days=7)

# 4. "Last Month" YoY Inflation (Full Preceding Month) (PERIOD AVERAGE)
last_month_end_date = get_last_day_of_previous_month(today)
last_month_start_date = get_first_day_of_previous_month(today)

last_month_compare_start = last_month_start_date.replace(year=last_month_start_date.year - 1)
last_month_compare_end = last_month_end_date.replace(year=last_month_end_date.year - 1)


# Function remains simplified, calculating RPI between two points (start_date to end_date)
def calculate_metric(name, start_date, end_date):
    """Calculates RPI for a given comparison period and returns results/exclusions."""

    # Calculate RPI from start_date (old price) to end_date (new price)
    rpi_final, excluded_final = calculate_rpi(
        DEFAULT_RPI_BASKET, start_date, end_date, mapping_dict, show_progress=False
    )

    return rpi_final, excluded_final

# New function signature for period average
def calculate_metric_period_avg(name, start_old, end_old, start_new, end_new):
    """Calculates RPI using period averages and returns results/exclusions."""

    rpi_final, excluded_final = calculate_rpi_period_average(
        DEFAULT_RPI_BASKET, start_old, end_old, start_new, end_new, mapping_dict, show_progress=False
    )
    return rpi_final, excluded_final


all_metrics = []
all_exclusions = {}

with st.spinner("Calculating current RPI metrics..."):

    # 1. 7-day YoY (Point-in-Time)
    rpi_yoy_7, exc_yoy_7 = calculate_metric("YoY (7-Day Point)", yoy_7_day_start, yoy_7_day_end)
    all_metrics.append({"label": "YoY (7-Day Point)", "value": rpi_yoy_7, "start": yoy_7_day_start, "end": yoy_7_day_end, "exclusions": exc_yoy_7})

    # 2. 30-day YoY (Point-in-Time)
    rpi_yoy_30, exc_yoy_30 = calculate_metric("YoY (30-Day Point)", yoy_30_day_start, yoy_30_day_end)
    all_metrics.append({"label": "YoY (30-Day Point)", "value": rpi_yoy_30, "start": yoy_30_day_start, "end": yoy_30_day_end, "exclusions": exc_yoy_30})

    # 3. Weekly Figure (MoM 7-Day) (Point-in-Time)
    rpi_weekly, exc_weekly = calculate_metric("MoM (Weekly Change)", weekly_start, weekly_end)
    all_metrics.append({"label": "MoM (Weekly Change)", "value": rpi_weekly, "start": weekly_start, "end": weekly_end, "exclusions": exc_weekly})

    # 4. Last Month YoY (Period Average - Graph Match)
    rpi_last_month, exc_last_month = calculate_metric_period_avg(
        "YoY (Last Full Month - Period Avg)",
        last_month_compare_start, last_month_compare_end, # Old period
        last_month_start_date, last_month_end_date      # New period
    )
    # Store period average metric with formatted date ranges
    all_metrics.append({
        "label": "YoY (Last Full Month Avg)",
        "value": rpi_last_month,
        "start": f"{last_month_compare_start} to {last_month_compare_end}",
        "end": f"{last_month_start_date} to {last_month_end_date}",
        "exclusions": exc_last_month
    })


# Consolidate all exclusions
for metric in all_metrics:
    all_exclusions[metric['label']] = metric['exclusions']


# --- Display Current RPI Figures as Scorecards ---
# Create 4 columns for the 4 key metrics
col1, col2, col3, col4 = st.columns(4)

# 1. YoY (7-Day Point)
with col1:
    m = all_metrics[0]
    st.metric(
        label="YoY (7-Day Point)",
        value=f"{m['value']:.2f}%" if m['value'] is not None else "N/A",
        delta=None, # Delta removed for clean scorecard look
        help=f"Inflation from {m['start']} to {m['end']}"
    )

# 2. YoY (30-Day Point)
with col2:
    m = all_metrics[1]
    st.metric(
        label="YoY (30-Day Point)",
        value=f"{m['value']:.2f}%" if m['value'] is not None else "N/A",
        delta=None,
        help=f"Inflation from {m['start']} to {m['end']}"
    )

# 3. MoM (Weekly Change)
with col3:
    m = all_metrics[2]
    # Calculate the weekly delta change from 7 days ago to today
    st.metric(
        label="MoM (Weekly Change)",
        value=f"{m['value']:.2f}%" if m['value'] is not None else "N/A",
        delta=None,
        help=f"Change from {m['start']} to {m['end']}"
    )

# 4. YoY (Last Full Month Avg)
with col4:
    m = all_metrics[3]
    # The help text now shows both the old and new period ranges
    st.metric(
        label="YoY (Last Full Month Avg)",
        value=f"{m['value']:.2f}%" if m['value'] is not None else "N/A",
        delta=None,
        help=f"Average inflation across the full month of {last_month_end_date.strftime('%B')} compared to one year prior."
    )


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
st.markdown("*Chart figures represent the Year-over-Year inflation based on the **average price** across the entire preceding month.*")
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
st.markdown("Use this tool to calculate the Weekly MoM and Last Month YoY RPI relative to a past date.")

historical_date = st.date_input("Select Historical Anchor Date", value=today - timedelta(days=365))

if st.button("Calculate Historical Metrics", type="secondary"):

    # Calculate Weekly MoM relative to historical date (7 days prior to selected date) (POINT-IN-TIME)
    h_weekly_end = historical_date
    h_weekly_start = historical_date - timedelta(days=7)

    h_rpi_weekly, h_exc_weekly = calculate_rpi(
        DEFAULT_RPI_BASKET, h_weekly_start, h_weekly_end, mapping_dict, show_progress=True
    )

    # Calculate Last Month YoY relative to historical date (PERIOD AVERAGE)
    h_last_month_end_date = get_last_day_of_previous_month(historical_date)
    h_last_month_start_date = get_first_day_of_previous_month(historical_date)

    h_last_month_compare_start = h_last_month_start_date.replace(year=h_last_month_start_date.year - 1)
    h_last_month_compare_end = h_last_month_end_date.replace(year=h_last_month_end_date.year - 1)

    h_rpi_last_month, h_exc_last_month = calculate_rpi_period_average(
        DEFAULT_RPI_BASKET,
        h_last_month_compare_start, h_last_month_compare_end,
        h_last_month_start_date, h_last_month_end_date,
        mapping_dict, show_progress=True
    )

    st.subheader(f"Results Relative to {historical_date}:\n*Note: Calculations use the price closest to the target date for point metrics, and averages for full-month metrics.*")

    h_col1, h_col2 = st.columns(2)

    with h_col1:
        st.metric(
            label=f"Weekly Change ({h_weekly_start} to {h_weekly_end}) (Point)",
            value=f"{h_rpi_weekly:.2f}%" if h_rpi_weekly is not None else "N/A"
        )

    with h_col2:
        st.metric(
            label=f"Last Month YoY ({h_last_month_compare_start} to {h_last_month_end_date}) (Avg)",
            value=f"{h_rpi_last_month:.2f}%" if h_rpi_last_month is not None else "N/A"
        )

    # Historical Exclusions
    all_h_excluded = list(set(h_exc_weekly + h_exc_last_month))
    if all_h_excluded:
        with st.expander("⚠️ Items Excluded from Historical Calculation"):
            st.markdown("The following items lacked price data for one or both comparison periods:")
            for item in all_h_excluded:
                st.markdown(f"- {item}")
