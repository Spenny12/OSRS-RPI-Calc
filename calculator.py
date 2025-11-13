import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from api_client import get_price_history
import calendar

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

    Returns a dictionary with results or an error message.
    """

    # 1. Find the item ID from the pre-processed mapping dictionary
    item_info = mapping_dict.get(item_name.lower())

    if not item_info:
        return {'error': f"ID not found for '{item_name}'. (Item name may be incorrect)"}

    # 2. Get the full price history from the Jagex API
    item_id = item_info['id']
    price_df = get_price_history(item_id)

    if price_df is None or price_df.empty:
        # --- THIS ERROR MESSAGE IS NOW CORRECT ---
        return {'error': f"No price data found for '{item_name}'. (The Wiki API may not list this item, or the request was blocked. Check User-Agent in config.py)"}

    try:
        # 3. Find the prices for the start and end dates
        # Use .asof() to find the closest price AT or BEFORE the target date
        old_price_data = price_df.asof(pd.to_datetime(start_date))
        new_price_data = price_df.asof(pd.to_datetime(end_date))

        # 4. Error checking for dates
        if old_price_data is None or pd.isna(old_price_data['avgHighPrice']):
            return {'error': f"No price data found for '{item_name}' on or before {start_date}. (Item may not have existed)"}

        if new_price_data is None or pd.isna(new_price_data['avgHighPrice']):
            return {'error': f"No price data found for '{item_name}' on or before {end_date}."}

        # 5. We have valid data, extract it
        old_price = old_price_data['avgHighPrice']
        new_price = new_price_data['avgHighPrice']

        # Get the actual dates from the dataframe index
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
            'price_df': price_df
        }

    except Exception as e:
        return {'error': f"An unexpected error occurred during calculation: {e}"}


def calculate_rpi(basket, start_date, end_date, mapping_dict, show_progress=True):
    """
    Calculates the weighted RPI for a basket of goods, handling missing items.
    """

    valid_results = []
    excluded_items = []
    total_valid_weight = 0.0

    if show_progress:
        progress_bar = st.progress(0, text="Initializing RPI calculation...")

    basket_items = list(basket.items())

    for i, (item_name, original_weight) in enumerate(basket_items):
        if show_progress:
            progress_text = f"Calculating for '{item_name.lower()}' ({i+1}/{len(basket_items)})..."
            progress_bar.progress((i+1) / len(basket_items), text=progress_text)

        # 1. Find the item ID
        item_info = mapping_dict.get(item_name.lower())

        if not item_info:
            excluded_items.append(f"{item_name} (ID not found)")
            continue

        # 2. Get price history
        item_id = item_info['id']
        price_df = get_price_history(item_id)

        if price_df is None or price_df.empty:
            excluded_items.append(f"{item_name} (No price data from Wiki API)")
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

    if show_progress:
        progress_bar.empty()

    # --- Final RPI Calculation (Re-weighting) ---

    if total_valid_weight == 0:
        # All items failed, return the exclusion list
        return None, excluded_items

    # Calculate the final weighted average
    final_rpi = 0.0
    for item in valid_results:
        # Re-calculate weight based on only the valid items
        new_weight = item['original_weight'] / total_valid_weight
        weighted_contribution = item['inflation'] * new_weight
        final_rpi += weighted_contribution

    return final_rpi, excluded_items


@st.cache_data(ttl="6h") # Cache the entire historical calculation for 6 hours
def calculate_monthly_rpi_dataframe(basket, mapping_dict):
    """
    Calculates the Year-over-Year (YoY) RPI for the last day of every month
    since data started, up to a reasonable limit.
    """

    today = date.today()
    current_date = date(today.year, today.month, 1) - timedelta(days=1) # Start at last day of last month

    rpi_data = []

    # Loop backwards to calculate RPI for each month
    # We will stop if the year becomes 2012 (before the API data existed)
    while current_date.year > 2012:

        # End date for the calculation (last day of the month)
        end_date = current_date

        # Start date for the YoY calculation (same day one year ago)
        start_date = date(current_date.year - 1, current_date.month, current_date.day)

        # Calculate RPI (silently)
        rpi_value, _ = calculate_rpi(basket, start_date, end_date, mapping_dict, show_progress=False)

        if rpi_value is not None:
            rpi_data.append({
                'Date': end_date,
                'YoY RPI (%)': rpi_value
            })

        # Move to the last day of the previous month
        if current_date.month == 1:
            current_date = date(current_date.year - 1, 12, 31)
        else:
            # Find the last day of the month before
            current_date = date(current_date.year, current_date.month, 1) - timedelta(days=1)

    if not rpi_data:
        return pd.DataFrame()

    df = pd.DataFrame(rpi_data)
    df = df.set_index('Date').sort_index()
    return df
