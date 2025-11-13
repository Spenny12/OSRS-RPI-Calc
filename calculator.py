import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
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
    The show_progress flag is used to suppress the Streamlit progress bar
    when running historical calculations on the Home page.
    """

    valid_results = []
    excluded_items = []
    total_valid_weight = 0.0

    progress_bar = None
    if show_progress:
        progress_bar = st.progress(0, text="Initializing RPI calculation...")

    for i, (item_name, original_weight) in enumerate(basket.items()):
        if show_progress:
            progress_text = f"Calculating for '{item_name.lower()}' ({i+1}/{len(basket)})..."
            progress_bar.progress((i+1) / len(basket), text=progress_text)

        # 1. Find the item ID
        item_info = mapping_dict.get(item_name.lower())

        if not item_info:
            excluded_items.append(f"{item_name} (ID not found)")
            continue

        # 2. Get price history
        item_id = item_info['id']
        # This function is cached, so repeated calls are fast
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

        # FIX: The NameError was fixed here in the previous step (new_row_price_data -> new_price_data)
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

    if progress_bar:
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

def calculate_monthly_rpi_dataframe(basket, num_months, mapping_dict):
    """
    Calculates the Year-over-Year RPI for the last N months.
    Returns a pandas DataFrame suitable for a Streamlit chart.
    """
    # Use the first day of the current month as the anchor
    today = datetime.now().date()
    current_month_start = today.replace(day=1)

    # DataFrame to store monthly results
    monthly_data = []

    # Calculate RPI for each month backwards
    for i in range(num_months):

        # Determine the target month's end (last day of the month we are calculating)
        # This month's end date is the 'new' date.

        # Calculate start date of the target month (e.g., Nov 1, 2024)
        target_month_start = (current_month_start - timedelta(days=1)).replace(day=1)

        # Calculate end date of the target month (e.g., Oct 31, 2024)
        target_month_end = current_month_start - timedelta(days=1)

        # The 'old' date is 1 year before the target month end (e.g., Oct 31, 2023)
        yoy_old_date = target_month_end - timedelta(days=365)

        # Run the RPI calculation (silently)
        rpi_value, _ = calculate_rpi(
            basket=basket,
            start_date=yoy_old_date,
            end_date=target_month_end,
            mapping_dict=mapping_dict,
            show_progress=False # Crucial for performance and UI cleanliness
        )

        # Store the result
        if rpi_value is not None:
            monthly_data.append({
                'Month': target_month_end,
                'YoY RPI (%)': rpi_value
            })

        # Move the anchor back one month
        current_month_start = target_month_start

    # Create DataFrame, set index, and sort chronologically
    df = pd.DataFrame(monthly_data)
    if df.empty:
        return pd.DataFrame({'Month': [], 'YoY RPI (%)': []})

    df['Month'] = pd.to_datetime(df['Month'])
    df = df.set_index('Month')
    df = df.sort_index()

    return df
