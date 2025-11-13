import streamlit as st
from datetime import datetime, timedelta
from api_client import get_item_mapping
from calculator import calculate_rpi
from config import DEFAULT_RPI_BASKET

st.set_page_config(page_title="OSRS Inflation Calculator", page_icon="📈", layout="wide")

st.title("OSRS Inflation Calculator")

st.markdown("""
Welcome! This tool calculates the inflation rate for items in Old School Runescape.

The "OSRS RPI" displayed below is a weighted inflation rate based on a default basket of popular items,
calculated from **one year ago (365 days) to today**.

Use the **"Custom Calculator"** page in the sidebar to:
- Calculate inflation for any single item.
- Build your own custom RPI basket.
- Select custom date ranges.
""")

# --- NEW: Changed default back to 365 days ---
st.header(f"Default OSRS 'RPI' (Last 365 Days)")

# --- Load Mapping Data ---
# Use a spinner for good user experience
with st.spinner("Loading OSRS item database..."):
    mapping_dict, item_names_list = get_item_mapping()

# --- Main App Logic ---
if mapping_dict and item_names_list:
    # --- RPI Calculation ---
    today = datetime.now().date()
    # --- NEW: Changed default back to 365 days ---
    start_date = today - timedelta(days=365)

    with st.spinner("Calculating default RPI..."):
        rpi_value, excluded_items = calculate_rpi(
            DEFAULT_RPI_BASKET,
            start_date,
            end_date=today,
            mapping_dict=mapping_dict
        )

    if rpi_value is not None:
        st.metric(
            label=f"Weighted Inflation ({start_date} to {today})",
            value=f"{rpi_value:.2f}%"
        )
        if excluded_items:
            st.warning(f"Some items were excluded from this calculation:")
            for item in excluded_items:
                st.markdown(f"- {item}")
    else:
        st.error("Could not calculate the RPI. No valid data was found for any item in the basket for this period.")
        if excluded_items:
            st.subheader("Reasons for failure:")
            st.markdown("All items in the basket failed. Here are the reasons:")
            for item in excluded_items:
                st.markdown(f"- {item}")

    st.subheader("Default Basket Definition")
    st.json({k: f"{v*100:.0f}%" for k, v in DEFAULT_RPI_BASKET.items()})

else:
    st.error("Failed to load OSRS item database. The API might be down. Please try again later.")
