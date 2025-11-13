import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from config import WEIRDGLOOP_HEADERS, MAPPING_HEADERS

@st.cache_data(ttl="6h")
def get_item_mapping():
    """
    Fetches the complete item ID-to-name mapping from the OSRS Wiki API.
    """
    try:
        response = requests.get(
            "https://prices.runescape.wiki/api/v1/osrs/mapping",
            headers=MAPPING_HEADERS
        )
        response.raise_for_status()
        mapping_data = response.json()

        mapping_dict = {}
        item_names_list = []

        for item in mapping_data:
            # Filter out placeholder/junk items
            if 'name' in item and 'id' in item and not item['name'].startswith("Exchange ticket"):
                item_name_lower = item['name'].lower()
                mapping_dict[item_name_lower] = {
                    'id': item['id'],
                    'name': item['name']
                }
                item_names_list.append(item['name'])

        item_names_list.sort() # Sort the list alphabetically for the UI

        return mapping_dict, item_names_list

    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching item mapping: {e}")
        return None, None

# Caching is re-enabled.
# This will store the data for 10 minutes to speed up the app.
@st.cache_data(ttl="10m")
def get_price_history(item_id):
    """
    Fetches full historical data using the 'all' endpoint and returns a DataFrame.
    """
    # This is the correct, final URL
    url = f"https://api.weirdgloop.org/exchange/history/osrs/all?id={item_id}"

    try:
        # Use the compliant headers for the 'weirdgloop' API
        response = requests.get(url, headers=WEIRDGLOOP_HEADERS)
        response.raise_for_status()

        price_data = response.json()

        # --- THIS IS THE FINAL FIX ---
        # The data is inside a key named after the item ID (e.g., "385")
        price_history = price_data.get(str(item_id), [])

        if not price_history:
            # This is the "empty 'data' list" error.
            # It means the API call worked, but there was no data.
            return None

        # --- Convert list of objects to a DataFrame ---
        df = pd.DataFrame(price_history)

        # --- Data Processing ---
        # Convert timestamp to datetime and set as index
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.set_index('date')

        # Rename 'price' to 'avgHighPrice' for consistency
        df = df.rename(columns={'price': 'avgHighPrice'})

        # Drop columns we don't need
        # We check if 'volume' exists before dropping, as it's not always present
        cols_to_drop = ['timestamp', 'id']
        if 'volume' in df.columns:
            cols_to_drop.append('volume')
        df = df.drop(columns=cols_to_drop, errors='ignore')

        # Ensure prices are numeric, coercing any errors to NaN
        df['avgHighPrice'] = pd.to_numeric(df['avgHighPrice'], errors='coerce')

        # Sort by date (CRITICAL for asof() and resample())
        df = df.sort_index()

        # Resample to a full daily index, taking the mean of any data on the same day
        df_daily = df.resample('D').mean()

        # Fill all gaps (weekends, holidays, etc.)
        # bfill() fills missing values at the *start* of the data
        # ffill() fills missing values *after* the first data point
        df_daily['avgHighPrice'] = df_daily['avgHighPrice'].bfill().ffill()

        return df_daily

    except requests.exceptions.RequestException:
        # This catches 4xx/5xx errors
        return None
    except Exception:
        # This catches JSON parsing errors or pandas errors
        return None
