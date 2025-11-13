import streamlit as st
import requests
import pandas as pd
from config import HEADERS
from datetime import datetime

# --- API Endpoints ---
# We use the Wiki API for MAPPING (fastest, most complete)
WIKI_API_URL = "https://prices.runescape.wiki/api/v1/osrs"
# We use the Jagex API for HISTORY (full, un-rounded historical data)
JAGEX_API_URL = "https://secure.runescape.com/m=itemdb_oldschool/api"


@st.cache_data(ttl="6h") # Cache the mapping data for 6 hours
def get_item_mapping():
    """
    Fetches the complete item ID-to-name mapping from the OSRS Wiki API.
    Processes it into a fast lookup dictionary and a sorted list of names.
    """
    try:
        response = requests.get(f"{WIKI_API_URL}/mapping", headers=HEADERS)
        response.raise_for_status()
        mapping_data = response.json()

        mapping_dict = {
            item['name'].lower(): {
                'id': item['id'],
                'examine': item.get('examine', ''),
                'members': item.get('members', False)
            }
            for item in mapping_data if 'name' in item and 'id' in item
        }

        item_names_list = sorted(item.lower() for item in mapping_dict.keys())

        return mapping_dict, item_names_list

    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching item mapping: {e}")
        return None, None

@st.cache_data(ttl="10m") # Cache price data for 10 minutes
def get_price_history(item_id):
    """
    Fetches the full, un-rounded, daily historical price data from the
    official Jagex API.
    """
    try:
        # --- NEW API ENDPOINT ---
        # Note: This API doesn't require the User-Agent header
        url = f"{JAGEX_API_URL}/graph/{item_id}.json"
        response = requests.get(url)
        response.raise_for_status()

        json_data = response.json()

        if 'daily' not in json_data or not json_data['daily']:
            # No daily price data found
            return None

        # --- NEW DATA FORMAT ---
        # Data is in: json_data['daily']
        # Format is: { "timestamp_in_ms_str": price_int, ... }
        # e.g., { "1394150400000": 332, ... }

        price_data = json_data['daily']

        # Convert to a DataFrame
        # Timestamps are in milliseconds
        df = pd.DataFrame(
            list(price_data.items()),
            columns=['timestamp_ms', 'price']
        )

        # Convert timestamps to datetime
        df['date'] = pd.to_datetime(df['timestamp_ms'], unit='ms')
        df = df.set_index('date')

        # --- STANDARDIZE COLUMN NAME ---
        # Rename 'price' to 'avgHighPrice' so all our
        # calculator logic still works perfectly.
        price_df = df[['price']].copy()
        price_df.rename(columns={'price': 'avgHighPrice'}, inplace=True)

        # Ensure it's numeric
        price_df['avgHighPrice'] = pd.to_numeric(price_df['avgHighPrice'])

        # Forward-fill to ensure we have data for every day
        # (The API only provides data for days with trades)
        daily_df = price_df.resample('D').mean()
        daily_df = daily_df.ffill()

        return daily_df

    except Exception as e:
        # Failed to process the data
        return None
