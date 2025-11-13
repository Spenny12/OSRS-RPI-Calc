import streamlit as st
from datetime import datetime, timedelta

# Import your custom modules
from config import DEFAULT_RPI_BASKET
from api_client import get_item_mapping
from calculator import calculate_rpi

# --- Page Configuration ---
st.set_page_config(
    page_title="OSRS Inflation Calculator",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- Main Page Content ---
st.title("📈 OSRS Inflation Calculator")
st.markdown("""
Welcome to the Old School Runescape Inflation Calculator!

This tool uses real-time price data from the [OSRS Wiki API](https://prices.runescape.wiki/) to
calculate in-game inflation rates.

The "OSRS RPI" displayed below is a 'Retail Price Index' for our default
basket of common items, calculated for the past 365 days.

Use the sidebar to navigate to the **Custom Calculator** to:
* Calculate inflation for any single item.
* Build your own custom basket of items and calculate its weighted inflation.
""")

# --- Load Mapping Data ---
# We need this to pass to the calculator
try:
    with st.spinner("Loading item database..."):
        mapping = get_item_mapping()
    
    if not mapping:
        st.error("Failed to load OSRS item database. The API might be down. Please try again later.", icon="🚨")
    else:
        # --- Default RPI Calculation ---
        st.header(f"Default 'RPI' (Last 365 Days)")
        
        with st.spinner("Calculating default RPI..."):
            today = datetime.now().date()
            start_date = today - timedelta(days=365)
            
            # Run the calculation
            rpi_value, excluded = calculate_rpi(DEFAULT_RPI_BASKET, start_date, today, mapping)
        
        if rpi_value is not None:
            # Display the main metric
            st.metric(
                label=f"Weighted Inflation ({start_date} to {today})",
                value=f"{rpi_value:.2f}%"
            )
            
            # Display the basket it was based on
            with st.expander("See default basket composition"):
                st.json({k: f"{v*100:.0f}% weight" for k, v in DEFAULT_RPI_BASKET.items()})

            # Display any warnings if items were excluded
            if excluded:
                st.warning(f"Some items were excluded from this calculation (e.g., did not exist): {', '.join(excluded)}")
        else:
            st.error("Could not calculate the RPI. No valid data was found for any item in the basket for this period.")

except Exception as e:
    st.error(f"An unexpected error occurred: {e}", icon="🔥")
