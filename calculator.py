import streamlit as st
import pandas as pd
from datetime import datetime
from api_client import get_price_history

def calculate_inflation_percent(old_price, new_price):
    """Calculates the percentage change between two prices."""
    if old_price is None or new_price is None or pd.isna(old_price) or pd.isna(new_price) or old_price == 0:
        return 0.0
    return ((new_price - old_price) / old_price) * 100.0

def calculate_single_item_inflation(item_name, start_date, end_date, mapping_dict):
    """
    Fetches data and calculates inflation for a single item.
    Returns a dictionary with results or an error message.
    """

    # --- NEW: Instant lookup from the dictionary ---
    item_info = mapping_dict.get(item_name.lower())

    if not item_info:
        return {'error': f"ID not found for '{item_name}'. (Item name may be incorrect)"}

    item_id = item_info['id']
    price_df = get_price_history(item_id)

    if price_df is None or price_df.empty:
        return {'error': f"API call failed or no price data found for '{item_name}'. (Timesteps 6h, 1h, 24h all failed)"}

    try:
        # Use .asof() to find the closest price to our dates
        old_price_data = price_df.asof(pd.to_datetime(start_date))
        new_price_data = price_df.asof(pd.to_datetime(end_date))

        # --- Error checking ---
        if old_price_data is None or pd.isna(old_price_data['avgHighPrice']):
            return {'error': f"No price data found for '{item_name}' on or before {start_date}. (Item may not have existed)"}

        if new_price_data is None or pd.isna(new_price_data['avgHighPrice']):
            return {'error': f"No price data found for '{item_name}' on or before {end_date}."}

        # --- Valid data, proceed ---
        old_price = old_price_data['avgHighPrice']
        new_price = new_price_data['avgHighPrice']

        # Get the actual dates of the prices found
        actual_start_date = old_price_data.name.date()
        actual_end_date = new_price_data.name.date()

        inflation_rate = calculate_inflation_percent(old_price, new_price)

        return {
            'error': None,
            'item_name': item_name,
            'inflation_rate': inflation_rate,
            'old_price': old_price,
            'new_price': new_price,
            'actual_start_date': actual_start_date,
            'actual_end_date': actual_end_date,
            'price_df': price_df
        }

    except Exception as e:
        return {'error': f"An unexpected error occurred during calculation: {e}"}


def calculate_rpi(basket, start_date, end_date, mapping_dict):
    """
    Calculates the weighted RPI for a basket of goods, handling missing items.
    Returns the final RPI value and a list of excluded items.
    """

    valid_results = []
    excluded_items = []
    total_valid_weight = 0.0

    # Use a progress bar for user feedback
    progress_bar = st.progress(0, text="Initializing RPI calculation...")

    for i, (item_name, original_weight) in enumerate(basket.items()):
        progress_text = f"Calculating for '{item_name.lower()}' ({i+1}/{len(basket)})..."
        progress_bar.progress((i+1) / len(basket), text=progress_text)

        # --- NEW: Instant lookup from the dictionary ---
        item_info = mapping_dict.get(item_name.lower())

        if not item_info:
            excluded_items.append(f"{item_name} (ID not found)")
            continue

        item_id = item_info['id']
        price_df = get_price_history(item_id)

        if price_df is None or price_df.empty:
            excluded_items.append(f"{item_name} (API call failed or no price data)")
            continue

        # Use .asof() to find the closest price
        old_price_data = price_df.asof(pd.to_datetime(start_date))
        new_price_data = price_df.asof(pd.to_datetime(end_date))

        # Check if price data exists at the start date.
        if old_price_data is None or pd.isna(old_price_data['avgHighPrice']):
            excluded_items.append(f"{item_name} (Did not exist at start date)")
            continue # Skip this item

        # Check for price at end date (less common, but possible)
        if new_price_data is None or pd.isna(new_price_data['avgHighPrice']):
            excluded_items.append(f"{item_name} (No data at end date)")
            continue # Skip this item

        # --- If we get here, the item is valid ---
        old_price = old_price_data['avgHighPrice']
        new_price = new_price_data['avgHighPrice']

        item_inflation = calculate_inflation_percent(old_price, new_price)

        valid_results.append({
            'name': item_name,
            'inflation': item_inflation,
            'original_weight': original_weight
        })
        total_valid_weight += original_weight

    progress_bar.empty() # Clear the progress bar

    # --- Final Calculation (Re-weighting) ---
    if total_valid_weight == 0:
        return None, excluded_items

    final_rpi = 0.0
    for item in valid_results:
        # Re-calculate weight based on only the valid items
        new_weight = item['original_weight'] / total_valid_weight
        weighted_contribution = item['inflation'] * new_weight
        final_rpi += weighted_contribution

    return final_rpi, excluded_items
