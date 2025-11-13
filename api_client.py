import streamlit as st
import requests
import pandas as pd
from config import HEADERS

API_BASE_URL = "https://prices.runescape.wiki/api/v1/osrs"

@st.cache_data(ttl="6h") # Cache the mapping data for 6 hours
def get_item_mapping():
    """Fetches the complete item ID-to-name mapping from the OSRS Wiki API."""
    try:
        response = requests.get(f"{API_BASE_URL}/mapping", headers=HEADERS)
        response.raise_for_status() # Raise an error for bad responses
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching item mapping: {e}")
        return None

@st.cache_data(ttl="10m") # Cache price data for 10 minutes
def get_price_history(item_id):
    """Fetches the 1-day timeseries data for a specific item ID."""
    try:
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
        
        # Forward-fill to handle days with no trades (common for rare items)
        # This prevents .asof() from grabbing a price from long ago
        price_df = price_df.ffill()
        
        return price_df
        
    except requests.exceptions.RequestException:
        # Don't show an error, just return None. The calculator will handle it.
        return None

def find_item_id(item_name, mapping):
    """Finds the item ID for a given item name from the mapping."""
    if not mapping:
        return None
    
    # Use a generator expression for a (slightly) faster lookup
    for item in mapping:
        if item['name'].lower() == item_name.lower():
            return item['id']
    return None
