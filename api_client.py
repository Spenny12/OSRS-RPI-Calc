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

# --- CRITICAL: Caching is DISABLED for debugging ---
# @st.cache_data(ttl="10m")
def get_price_history(item_id):
    """
    Fetches full historical data and returns a (DataFrame, debug_info) tuple.
    Caching is disabled to allow for live debugging of API responses.
    """
    url = f"https://api.weirdgloop.org/exchange/history/osrs/all?id={item_id}"

    # This dictionary will hold all our debug info
    debug_info = {
        "url": url,
        "status_code": None,
        "response_text": None,
        "error": None
    }

    try:
        response = requests.get(url, headers=WEIRDGLOOP_HEADERS)
        debug_info["status_code"] = response.status_code
        debug_info["response_text"] = response.text

        response.raise_for_status() # Will trigger error if status is 4xx or 5xx

        price_data = response.json()
        price_history = price_data.get('data', [])

        if not price_history:
            # This is a successful call but with no data
            debug_info["error"] = "API returned a successful response but with an empty 'data' list."
            return None, debug_info

        # --- Convert list of objects to a DataFrame ---
        df = pd.DataFrame(price_history)

        # --- CRITICAL FIXES ---
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.set_index('date')
        df = df.rename(columns={'price': 'avgHighPrice'})
        df = df.drop(columns=['timestamp', 'volume'])
        df['avgHighPrice'] = pd.to_numeric(df['avgHighPrice'], errors='coerce')
        df = df.sort_index()
        df_daily = df.resample('D').mean()
        df_daily['avgHighPrice'] = df_daily['avgHighPrice'].bfill().ffill()

        # Success! Return the data and the debug info
        return df_daily, debug_info

    except requests.exceptions.RequestException as e:
        # This catches HTTP errors (e.g., 404, 500)
        debug_info["error"] = f"RequestException: {e}"
        return None, debug_info
    except Exception as e:
        # This catches other errors, like JSON parsing
        debug_info["error"] = f"ProcessingException: {e}"
        # response_text will already be set, so we can debug it
        return None, debug_info
