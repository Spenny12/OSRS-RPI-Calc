import streamlit as st
import pandas as pd
from datetime import datetime
from api_client import get_price_history

def calculate_inflation_percent(old_price, new_price):
    """
    Helper function to calculate percentage change.
    Returns 0.0 if old_price is missing or zero.
    """
    if old_price is None or new_price is None or pd.isna(old_price) or pd.isna(new_price) or old_price == 0:
        return 0.0
    return ((new_price - old_price) / old_price) * 100.0

def calculate_single_item_inflation(item_name, start_date, end_date, mapping_dict):
    """
    Calculates inflation for a single item over a period.

    Returns a dictionary with results, an error message, and new debug info.
    """

    # 1. Find the item ID
    item_info = mapping_dict.get(item_name.lower())
    debug_info = {} # Initialize debug info

    if not item_info:
        return {
            'error': f"ID not found for '{item_name}'. (Item name may be incorrect)",
            'debug_info': {'error': 'Item not found in local mapping dictionary.'}
        }

    # 2. Get the full price history AND debug info
    item_id = item_info['id']
    price_df, debug_info = get_price_history(item_id)

    if price_df is None or price_df.empty:
        # The API call failed, return the error and the debug info
        return {
            'error': f"No price data found for '{item_name}'. Check debug info below for API response.",
            'debug_info': debug_info
        }

    try:
        # 3. Find the prices for the start and end dates
        old_price_data = price_df.asof(pd.to_datetime(start_date))
        new_price_data = price_df.asof(pd.to_datetime(end_date))

        # 4. Error checking for dates
        if old_price_data is None or pd.isna(old_price_data['avgHighPrice']):
            return {
                'error': f"No price data found for '{item_name}' on or before {start_date}. (Item may not have existed)",
                'debug_info': debug_info
            }

        if new_price_data is None or pd.isna(new_price_data['avgHighPrice']):
            return {
                'error': f"No price data found for '{item_name}' on or before {end_date}.",
                'debug_info': debug_info
            }

        # 5. We have valid data, extract it
        old_price = old_price_data['avgHighPrice']
        new_price = new_price_data['avgHighPrice']
        actual_start_date = old_price_data.name.date()
        actual_end_date = new_price_data.name.date()

        # 6. Calculate inflation
        inflation_rate = calculate_inflation_percent(old_price, new_price)

        # 7. Return the complete result object
        return {
            'error': None,
            'item_name': item_name,
            'inflation_rate': inflation_rate,
            'old_price': old_price,
            'new_price': new_price,
            'actual_start_date': actual_start_date,
            'actual_end_date': actual_end_date,
            'price_df': price_df,
            'debug_info': debug_info # Pass the debug info
        }

    except Exception as e:
        debug_info['error'] = f"Pandas .asof() Error: {e}"
        return {
            'error': f"An unexpected error occurred during calculation: {e}",
            'debug_info': debug_info
        }


def calculate_rpi(basket, start_date, end_date, mapping_dict):
    """
    Calculates the weighted RPI for a basket of goods, handling missing items.
    """

    valid_results = []
    excluded_items = []
    total_valid_weight = 0.0

    progress_bar = st.progress(0, text="Initializing RPI calculation...")

    for i, (item_name, original_weight) in enumerate(basket.items()):
        progress_text = f"Calculating for '{item_name.lower()}' ({i+1}/{len(basket)})..."
        progress_bar.progress((i+1) / len(basket), text=progress_text)

        # 1. Find the item ID
        item_info = mapping_dict.get(item_name.lower())

        if not item_info:
            excluded_items.append(f"{item_name} (ID not found)")
            continue

        # 2. Get price history (and ignore debug info for RPI)
        item_id = item_info['id']
        price_df, debug_info = get_price_history(item_id) # Caching is off, this will be slow

        if price_df is None or price_df.empty:
            # Pass up the API error from debug info
            api_error = debug_info.get('error', 'No data')
            excluded_items.append(f"{item_name} (API Error: {api_error})")
            continue

        # 3. Find prices at target dates
        old_price_data = price_df.asof(pd.to_datetime(start_date))
        new_price_data = price_df.asof(pd.to_datetime(end_date))

        # 4. Check if data exists for those dates
        if old_price_data is None or pd.isna(old_price_data['avgHighPrice']):
            excluded_items.append(f"{item_name} (Did not exist at start date)")
            continue

        if new_price_data is None or pd.isna(new_price_data['avgHighPrice']):
            excluded_items.append(f"{item_name} (No data at end date)")
            continue

        # 5. Data is valid! Calculate item-specific inflation
        old_price = old_price_data['avgHighPrice']
        new_price = new_price_data['avgHighPrice']

        item_inflation = calculate_inflation_percent(old_price, new_price)

        valid_results.append({
            'name': item_name,
            'inflation': item_inflation,
            'original_weight': original_weight
        })
        total_valid_weight += original_weight

    progress_bar.empty()

    # --- Final RPI Calculation (Re-weighting) ---

    if total_valid_weight == 0:
        return None, excluded_items

    final_rpi = 0.0
    for item in valid_results:
        new_weight = item['original_weight'] / total_valid_weight
        weighted_contribution = item['inflation'] * new_weight
        final_rpi += weighted_contribution

    return final_rpi, excluded_items
