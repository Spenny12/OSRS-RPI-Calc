import streamlit as st
import requests
import pandas as pd
from datetime import datetime
# --- NEW: Import both headers ---
from config import WEIRDGLOOP_HEADERS, MAPPING_HEADERS

@st.cache_data(ttl="6h")
def get_item_mapping():
    """
    Fetches the complete item ID-to-name mapping from the OSRS Wiki API.
    This function remains the same, as it's the best way to get IDs.
    """
    try:
        response = requests.get(
            "https://prices.runescape.wiki/api/v1/osrs/mapping",
            # --- NEW: Use the MAPPING_HEADERS ---
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
                item_names_list.append(item['name']) # Use the proper cased name for the list

        item_names_list.sort()

        return mapping_dict, item_names_list

    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching item mapping: {e}")
        return None, None

@st.cache_data(ttl="10m")
def get_price_history(item_id):
    """
    --- FINAL FIX: Fetches full historical data using the 'all' endpoint ---
    This is the underlying API the OSRS Wiki uses for its historical charts.
    It provides the complete, non-truncated history for all items.
    """
    try:
        # --- THIS IS THE CORRECTED API ENDPOINT ---
        # The filter is 'all', and the item ID is a query parameter.
        url = f"https://api.weirdgloop.org/exchange/history/osrs/all?id={item_id}"

        # --- NEW: Use the WEIRDGLOOP_HEADERS ---
        response = requests.get(url, headers=WEIRDGLOOP_HEADERS)
        response.raise_for_status()

        # This API now returns a single object: {"id": 385, "name": "Shark", "data": [...]}
        # We only care about the 'data' list.
        price_data = response.json()
        price_history = price_data.get('data', [])

        if not price_history:
            return None

        # --- Convert list of objects to a DataFrame ---
        df = pd.DataFrame(price_history)

        # --- CRITICAL FIXES ---

        # 1. Convert timestamp (which is in milliseconds) to datetime
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.set_index('date')

        # 2. Rename the 'price' column to match our existing code
        df = df.rename(columns={'price': 'avgHighPrice'})

        # 3. Drop columns we don't need before resampling
        df = df.drop(columns=['timestamp', 'volume'])

        # 4. Ensure price is numeric, coercing errors
        df['avgHighPrice'] = pd.to_numeric(df['avgHighPrice'], errors='coerce')

        # 5. CRITICAL: Sort the index. asof() requires a sorted index.
        df = df.sort_index()

        # 6. Resample to a full daily index ('D') and get the mean.
        #    (This handles if there are multiple trades in one day)
        df_daily = df.resample('D').mean()

        # 7. Fill all gaps. bfill() fills NaNs at the start, ffill() fills the rest.
        df_daily['avgHighPrice'] = df_daily['avgHighPrice'].bfill().ffill()

        return df_daily

    except requests.exceptions.RequestException:
        # This will catch 404s (for items this API doesn't track)
        return None
    except Exception:
        # Catch other errors, like JSON parsing
        return None
