import pandas as pd
from api_client import get_price_history, find_item_id
import streamlit as st

def get_item_price_on_date(price_df, target_date):
    """
    Safely gets the price data for a target date from a price dataframe.

    Returns a dictionary {'price': N, 'actual_date': Y} or None.
    """
    if price_df is None or price_df.empty:
        return None

    # Use .asof() to find the closest price row at or before the target_date
    price_row = price_df.asof(pd.to_datetime(target_date))

    # .asof() returns None if target_date is before the first date in the index
    if price_row is None or pd.isna(price_row['avgHighPrice']):
        return None

    return {
        'price': price_row['avgHighPrice'],
        'actual_date': price_row.name.date()
    }

def calculate_inflation(old_price, new_price):
    """Calculates the percentage change between two prices."""
    if old_price is None or new_price is None or old_price == 0 or pd.isna(old_price) or pd.isna(new_price):
        return 0
    return ((new_price - old_price) / old_price) * 100

def calculate_rpi(basket, start_date, end_date, mapping):
    """
    Calculates the weighted RPI for a basket of goods, handling missing items
    and providing detailed error reasons.
    """
    valid_results = []
    excluded_items = []
    total_valid_weight = 0.0

    # Use a progress bar for user feedback during API calls
    progress_bar = st.progress(0, text="Initializing RPI calculation...")

    for i, (item_name, original_weight) in enumerate(basket.items()):
        progress_text = f"Calculating for '{item_name}' ({i+1}/{len(basket)})..."
        progress_bar.progress((i+1) / len(basket), text=progress_text)

        # 1. Check for Item ID
        item_id = find_item_id(item_name, mapping)
        if not item_id:
            excluded_items.append(f"{item_name} (ID not found)")
            continue

        # 2. Check API Response
        price_df = get_price_history(item_id)
        if price_df is None or price_df.empty:
            # THIS IS THE NEW, CLEARER ERROR
            excluded_items.append(f"{item_name} (API call failed or no price data)")
            continue

        # 3. Check for Old Price
        old_price_data = get_item_price_on_date(price_df, start_date)
        if old_price_data is None:
            # This is now the ONLY way to get this specific message
            excluded_items.append(f"{item_name} (Did not exist at start date)")
            continue

        # 4. Check for New Price
        new_price_data = get_item_price_on_date(price_df, end_date)
        if new_price_data is None:
            excluded_items.append(f"{item_name} (No data at end date)")
            continue

        # --- If we get here, the item is valid ---
        item_inflation = calculate_inflation(old_price_data['price'], new_price_data['price'])

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
