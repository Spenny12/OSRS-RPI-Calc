import streamlit as st
import pandas as pd

# Import your custom modules
from api_client import get_price_history, find_item_id

def get_item_price_on_date(price_df, target_date):
    """
    Safely gets the price of an item on a target date using .asof()
    
    Returns a dict {'price': N, 'actual_date': YYYY-MM-DD} or None
    """
    if price_df is None or price_df.empty:
        return None
        
    # Use .asof() to find the closest price row at or before the target date
    price_row = price_df.asof(pd.to_datetime(target_date))
    
    # Check if the found data is valid
    if price_row is None or pd.isna(price_row['avgHighPrice']):
        return None # No data found at or before this date
        
    return {
        'price': price_row['avgHighPrice'],
        'actual_date': price_row.name.date() # The date of the price we found
    }

def calculate_inflation(old_price, new_price):
    """Calculates the percentage change between two prices."""
    if old_price is None or new_price is None or old_price == 0:
        return 0.0
    return ((new_price - old_price) / old_price) * 100.0

def calculate_rpi(basket, start_date, end_date, mapping):
    """
    Calculates the weighted RPI for a basket of goods, handling missing items.
    
    Returns: (final_rpi, list_of_excluded_items)
    """
    
    valid_results = []
    excluded_items = []
    total_valid_weight = 0.0

    # Show progress bar in the main app area
    progress_bar = st.progress(0, text="Initializing RPI calculation...")
    
    for i, (item_name, original_weight) in enumerate(basket.items()):
        progress_text = f"Processing '{item_name}' ({i+1}/{len(basket)})..."
        progress_bar.progress((i+1) / len(basket), text=progress_text)

        item_id = find_item_id(item_name, mapping)
        if not item_id:
            excluded_items.append(f"{item_name} (ID not found)")
            continue

        price_df = get_price_history(item_id)
        
        # Get prices for start and end dates
        old_price_data = get_item_price_on_date(price_df, start_date)
        new_price_data = get_item_price_on_date(price_df, end_date)

        # --- Validation Logic ---
        if old_price_data is None:
            excluded_items.append(f"{item_name} (Did not exist at start date)")
            continue # Skip this item
        if new_price_data is None:
            excluded_items.append(f"{item_name} (No data at end date)")
            continue # Skip this item

        # --- If we get here, the item is valid ---
        item_inflation = calculate_inflation(old_price_data['price'], new_price_data['price'])
        
        valid_results.append({
            'name': item_name,
            'inflation': item_inflation,
            'original_weight': original_weight,
            'old_price': old_price_data['price'],
            'new_price': new_price_data['price']
        })
        total_valid_weight += original_weight

    progress_bar.empty() # Remove progress bar when done

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
