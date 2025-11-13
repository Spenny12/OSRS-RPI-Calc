import streamlit as st
from datetime import datetime, timedelta
from api_client import get_item_mapping
from calculator import calculate_single_item_inflation, calculate_rpi
import pandas as pd

st.set_page_config(page_title="Custom Calculator", page_icon="🎛️", layout="wide")
st.title("🎛️ Custom Inflation Calculator")

# --- Load Mapping Data ---
# Caching is re-enabled
@st.cache_data(ttl="6h")  # Cache this for 6 hours
def load_mapping_data():
    """Helper to cache the mapping data."""
    return get_item_mapping()

mapping_dict, item_names_list = load_mapping_data()

if not mapping_dict or not item_names_list:
    # This line was fixed. It was missing the closing ")
    st.error("Failed to load item mapping data from the Wiki API. The app cannot continue. Please try refreshing.")
    st.stop() # Added st.stop() because the app can't run without this data.
