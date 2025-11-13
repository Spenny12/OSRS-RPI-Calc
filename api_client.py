import requests
import pandas as pd
import streamlit as st
from config import HEADERS # Import HEADERS from config

# --- Item ID Mapping ---
@st.cache_resource(ttl="6h")
def get_item_mapping():
    """
    Fetches the OSRS Wiki ID/name mapping.

    Returns:
        tuple: (mapping_dict, item_names_list)
        - mapping_dict: {'shark': {'id': 385, 'name': 'Shark'}, ...}
        - item_names_list: ['shark', 'twisted bow', ...]
    """
    WIKI_MAPPING_URL = "https://prices.runescape.wiki/api/v1/osrs/mapping"
    try:
        response = requests.get(WIKI_MAPPING_URL, headers=HEADERS)
        response.raise_for_status()
        data = response.json()

        mapping_dict = {}
        item_names_list = []

        for item in data:
            # Ensure item has a name, id, and is tradeable (examine text)
            if 'name' in item and 'id' in item and 'examine' in item:
                lowered_name = item['name'].lower()
                mapping_dict[lowered_name] = item
                item_names_list.append(lowered_name)

        return mapping_dict, sorted(item_names_list)

    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching OSRS item mapping: {e}")
        return None, None

# --- Price History (Jagex API) ---
@st.cache_data(ttl="1h")
def get_price_history(item_id):
    """
    Fetches the full, un-rounded price history for an item from the Jagex API.
    """
    JAGEX_GRAPH_URL = f"https://services.runescape.com/m=itemdb_oldschool/api/graph/{item_id}.json"

    try:
        response = requests.get(JAGEX_GRAPH_URL, headers=HEADERS)
        response.raise_for_status()
        data = response.json()

        # The data is in a dictionary {'timestamp': price}
        # We need to convert it to a DataFrame
        price_history = data.get('daily', {})
        if not price_history:
            return None # Item may be new or not tracked

        df = pd.DataFrame(list(price_history.items()), columns=['timestamp', 'avgHighPrice'])

        # Convert timestamps (which are in milliseconds) to datetime objects
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.set_index('date')

        # --- THIS IS THE CRITICAL FIX ---
        # The dictionary is unsorted, so the DataFrame index is jumbled.
        # We MUST sort by date before we can use .asof() or resample.
        df = df.sort_index()

        # Resample to daily (D) and forward-fill missing days (weekends, etc.)
        # This gives us a clean, continuous price history.
        df_daily = df.resample('D').mean()
        df_daily['avgHighPrice'] = df_daily['avgHighPrice'].ffill()

        # Create 'avgLowPrice' as a placeholder since this API doesn't provide it
        # Our calculator only uses 'avgHighPrice' anyway
        df_daily['avgLowPrice'] = df_daily['avgHighPrice']

        return df_daily

    except requests.exceptions.RequestException as e:
        # Handle cases where the item doesn't exist on the graph API (e.g., item ID 1)
        st.warning(f"Could not fetch price graph for item ID {item_id}: {e}")
        return None
