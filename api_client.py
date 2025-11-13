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
            if 'name' in item and 'id' in item and not item['name'].startswith("Exchange ticket"):
                item_name_lower = item['name'].lower()
                mapping_dict[item_name_lower] = {
                    'id': item['id'],
                    'name': item['name']
                }
                item_names_list.append(item['name'])

        item_names_list.sort()

        return mapping_dict, item_names_list

    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching item mapping: {e}")
        return None, None

# --- Caching is now RE-ENABLED ---
@st.cache_data(ttl="10m")
def get_price_history(item_id):
    """
    Fetches full historical data using the 'all' endpoint and returns a DataFrame.
    """
    url = f"https://api.weirdgloop.org/exchange/history/osrs/all?id={item_id}"

    try:
        response = requests.get(url, headers=WEIRDGLOOP_HEADERS)
        response.raise_for_status()

        price_data = response.json()

        # --- THIS IS THE FINAL BUG FIX ---
        # The data is in a key named after the item_id (e.g., "385")
        # not a key named "data".
        price_history = price_data.get(str(item_id), [])

        if not price_history:
            return None # API returned no data for this item

        # --- Convert list of objects to a DataFrame ---
        df = pd.DataFrame(price_history)

        # --- Data Processing ---
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.set_index('date')
        df = df.rename(columns={'price': 'avgHighPrice'})

        # Safely drop columns that may or may not exist
        cols_to_drop = ['timestamp', 'volume', 'id']
        for col in cols_to_drop:
            if col in df.columns:
                df = df.drop(columns=[col])

        df['avgHighPrice'] = pd.to_numeric(df['avgHighPrice'], errors='coerce')
        df = df.sort_index()

        # Resample to daily, then fill gaps
        df_daily = df.resample('D').mean()
        df_daily['avgHighPrice'] = df_daily['avgHighPrice'].bfill().ffill()

        return df_daily

    except requests.exceptions.RequestException:
        return None
    except Exception:
        # Catch any other processing errors (like JSON parsing)
        return None
