import streamlit as st
import requests
import pandas as pd
from config import HEADERS
from datetime import datetime

API_BASE_URL = "https://prices.runescape.wiki/api/v1/osrs"

@st.cache_data(ttl="6h") # Cache the mapping data for 6 hours
def get_item_mapping():
    """
    Fetches the complete item ID-to-name mapping and processes it into
    a fast lookup dictionary and a sorted list of names.
    """
    try:
        response = requests.get(f"{API_BASE_URL}/mapping", headers=HEADERS)
        response.raise_for_status() # Raise an error for bad responses (4xx or 5xx)

        mapping_data = response.json()

        # --- NEW: Process into a high-speed dictionary (hash map) ---
        # This makes lookups instantaneous: mapping_dict['Shark'] -> 385
        mapping_dict = {
            item['name'].lower(): {
                'id': item['id'],
                'examine': item.get('examine', ''),
                'members': item.get('members', False)
            }
            for item in mapping_data if 'name' in item and 'id' in item
        }

        # Get a sorted list of item names for the UI
        item_names_list = sorted(item.lower() for item in mapping_dict.keys())

        return mapping_dict, item_names_list

    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching item mapping: {e}")
        return None, None

@st.cache_data(ttl="10m") # Cache price data for 10 minutes
def get_price_history(item_id):
    """
    Fetches price history for an item, trying multiple timesteps for resilience.
    It will try '6h', '1h', and '24h' in order.
    """

    # --- NEW: Resilient API Fallback Logic ---
    # We try '6h' first (good balance), then '1h' (for low-vol items),
    # then '24h' (as a last resort).
    timesteps_to_try = ['6h', '1h', '24h']
    data = None

    for timestep in timesteps_to_try:
        try:
            url = f"{API_BASE_URL}/timeseries?id={item_id}&timestep={timestep}"
            response = requests.get(url, headers=HEADERS)
            response.raise_for_status()

            json_data = response.json()
            if json_data.get('data'):
                data = json_data['data']
                # Found data, stop trying
                break

        except requests.exceptions.RequestException:
            # This timestep failed (e.g., 404), try the next one
            continue

    if not data:
        # We tried all timesteps and none worked or returned data
        return None

    # --- Process the data we found ---
    try:
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['timestamp'], unit='s')
        df = df.set_index('date')

        price_df = df[['avgHighPrice', 'avgLowPrice']].copy()
        price_df['avgHighPrice'] = pd.to_numeric(price_df['avgHighPrice'])
        price_df['avgLowPrice'] = pd.to_numeric(price_df['avgLowPrice'])

        # Forward-fill any missing data points within the *original* timestep
        price_df = price_df.ffill()

        # Resample to a consistent daily average ('D')
        daily_avg_df = price_df.resample('D').mean()

        # Forward-fill the *daily* data to fill in days with no trades
        daily_avg_df = daily_avg_df.ffill()

        return daily_avg_df

    except Exception:
        # Failed to process the data (e.g., empty, corrupt)
        return None
