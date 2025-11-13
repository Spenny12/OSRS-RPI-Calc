import streamlit as st
import requests
import pandas as pd
from config import HEADERS

API_BASE_URL = "https://prices.runescape.wiki/api/v1/osrs"

@st.cache_data(ttl="1d") # Cache the mapping data for 6 hours
def get_item_mapping():
    """Fetches the complete item ID-to-name mapping from the OSRS Wiki API."""
    try:
        response = requests.get(f"{API_BASE_URL}/mapping", headers=HEADERS)
        response.raise_for_status() # Raise an error for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching item mapping: {e}")
        return None

@st.cache_data(ttl="10m") # Cache price data for 10 minutes
def get_price_history(item_id):
    """
    Fetches the 6-HOUR timeseries data for a specific item ID
    and resamples it to a daily average.
    """
    try:
        # --- THIS IS THE CHANGE ---
        # We now fetch '1d' data to get a good balance of
        # full history and manageable response size.
        response = requests.get(f"{API_BASE_URL}/timeseries?id={item_id}&timestep=1d", headers=HEADERS)
        response.raise_for_status()
        data = response.json().get('data', [])

        if not data:
            return None

        # Load into a pandas DataFrame
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['timestamp'], unit='s')
        df = df.set_index('date')

        # Select and clean price data
        price_df = df[['avgHighPrice', 'avgLowPrice']].copy()
        price_df['avgHighPrice'] = pd.to_numeric(price_df['avgHighPrice'])
        price_df['avgLowPrice'] = pd.to_numeric(price_df['avgLowPrice'])

        # Forward-fill any missing 6-hour data points
        price_df = price_df.ffill()

        # --- NEW LOGIC: Resample 1d data to daily data ---
        # 'D' means daily. We take the mean() of all hours for each day.
        # This creates a robust daily average.
        daily_avg_df = price_df.resample('D').mean()

        # Forward-fill the *daily* data to fill in any days
        # with no trades (e.g., system updates, weekends for rare items)
        daily_avg_df = daily_avg_df.ffill()

        return daily_avg_df

    except requests.exceptions.RequestException:
        # If the API call fails (404, 500, timeout, etc.), return None
        return None

def find_item_id(item_name, mapping):
    """Finds the item ID for a given item name from the mapping."""
    if not mapping:
        return None

    for item in mapping:
        if item['name'].lower() == item_name.lower():
            return item['id']
    return None
