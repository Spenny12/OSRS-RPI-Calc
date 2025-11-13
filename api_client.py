import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from config import HEADERS

@st.cache_data(ttl="6h")
def get_item_mapping():
    """
    Fetches the complete item ID-to-name mapping from the OSRS Wiki API.
    Processes the data into a fast lookup dictionary and a sorted list of names.
    """
    try:
        response = requests.get(
            "https://prices.runescape.wiki/api/v1/osrs/mapping",
            headers=HEADERS
        )
        response.raise_for_status()
        mapping_data = response.json()

        # --- NEW: Process into a high-speed dictionary ---
        # Key: item name (lowercase)
        # Value: {'id': 123, 'name': "Item Name"}
        mapping_dict = {}
        item_names_list = []

        for item in mapping_data:
            # Ensure the item has a name and isn't a placeholder
            if 'name' in item and 'id' in item and not item['name'].startswith("Exchange ticket"):
                item_name_lower = item['name'].lower()
                mapping_dict[item_name_lower] = {
                    'id': item['id'],
                    'name': item['name'] # Store the original case-sensitive name
                }
                item_names_list.append(item_name_lower)

        # Sort the list for the UI
        item_names_list.sort()

        return mapping_dict, item_names_list

    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching item mapping: {e}")
        return None, None

@st.cache_data(ttl="10m")
def get_price_history(item_id):
    """
    Fetches the full historical graph data from the Jagex API for a specific item ID.
    This provides un-rounded, daily data for the item's entire history.
    """
    try:
        # --- NEW: Using the Jagex API for full history ---
        url = f"https://services.runescape.com/m=itemdb_oldschool/api/graph/{item_id}.json"

        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        data = response.json()

        # The 'daily' key holds a dictionary of: {timestamp: price}
        price_history = data.get('daily')

        if not price_history:
            # This can happen for items Jagex doesn't list
            return None

        # --- Convert dictionary to a DataFrame ---
        df = pd.DataFrame(
            list(price_history.items()),
            columns=['timestamp', 'avgHighPrice']
        )

        # --- CRITICAL FIXES ---

        # 1. Convert timestamp (which is a string) to numeric, then to datetime
        #    This is the safest way to handle the API's string timestamps.
        df['date'] = pd.to_datetime(pd.to_numeric(df['timestamp']), unit='ms')
        df = df.set_index('date')

        # 2. Drop the now-useless timestamp column BEFORE resampling
        df = df.drop(columns=['timestamp'])

        # 3. Ensure price is numeric, coercing errors
        df['avgHighPrice'] = pd.to_numeric(df['avgHighPrice'], errors='coerce')

        # 4. CRITICAL: Sort the index. asof() requires a sorted index.
        df = df.sort_index()

        # 5. Resample to a full daily index ('D') and get the mean.
        #    This creates a clean, gap-less daily timeline.
        df_daily = df.resample('D').mean()

        # 6. Fill all gaps.
        #    ffill() fills gaps after the item's release.
        #    bfill() fills gaps at the *start* of the data (e.g., if Jagex
        #    has data starting from 2014, this fills backward to the
        #    beginning of pandas' default time, which is fine for .asof())
        df_daily['avgHighPrice'] = df_daily['avgHighPrice'].ffill().bfill()

        return df_daily

    except requests.exceptions.RequestException:
        # This will catch 404s (for items Jagex doesn't track) or other errors
        return None
    except Exception:
        # Catch other errors, like JSON parsing
        return None
