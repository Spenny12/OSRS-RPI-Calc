import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from api_client import get_price_history
from math import floor

def calculate_inflation_percent(old_price, new_price):
    """
    Helper function to calculate percentage change.
    Returns 0.0 if old_price is missing or zero.
    """
    if old_price is None or new_price is None or pd.isna(old_price) or pd.isna(new_price) or old_price == 0:
        return 0.0
    return ((new_price - old_price) / old_price) * 100.0

def get_average_price_for_period(item_id, start_date, end_date):
    """
    Retrieves and calculates the average price of an item between start_date and end_date (inclusive).
    Returns the average price or None if data is insufficient.
    """
    price_df = get_price_history(item_id)
    if price_df is None or price_df.empty:
        return None

    # Filter the price history DataFrame to the requested period
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)

    # Simple filtering on the index (date)
    period_df = price_df[(price_df.index >= start_dt) & (price_df.index <= end_dt)]

    # Check if we have at least 1 day of data in the period
    if period_df.empty:
        # Fallback: check if the item existed at all before the start date.
        if price_df.index.max() < start_dt:
             return None # Item did not exist/was not tracked yet

    # Calculate the mean of the avgHighPrice over the period
    # If using API data, we are averaging the available daily high prices.
    avg_price = period_df['avgHighPrice'].mean()

    return avg_price

def calculate_single_item_inflation(item_name, start_date, end_date, mapping_dict):
    """
    Calculates inflation for a single item over a period (point-to-point).

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
        return {'error': f"No price data found for '{item_name}'. (The Wiki API may not list this item, or the request was blocked. Check User-Agent in config.py)"}

    try:
        # 3. Find the prices for the start and end dates (Point-in-time calculation using .asof())
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


@st.cache_data(ttl="1h") # Cache the entire historical calculation for 1 hour
def calculate_monthly_rpi_dataframe(basket, mapping_dict):
    """
    Generates a DataFrame of monthly YoY RPI figures spanning the entire available history.
    Each point represents the YoY inflation of the *average price* across that full month.
    """

    today = datetime.now().date()
    # Start at the 1st of the current month
    current_date = date(today.year, today.month, 1)

    rpi_data = []

    # Set a safe limit (e.g., 20 years) to prevent infinite loops if data is sparse
    max_months = 240

    for _ in range(max_months):
        # Determine the full month period for the current calculation (e.g., October 1 to October 31)
        # The end date is the last day of the month before the current 'current_date' (which is the 1st of a month)
        end_of_month = current_date - timedelta(days=1)
        start_of_month = date(end_of_month.year, end_of_month.month, 1)

        # We need the YoY comparison period as well (the same month, one year prior)

        # --- FIX: Added try/except to handle ValueError when replacing Feb 29th in a non-leap year ---
        try:
            start_of_year_ago = start_of_month.replace(year=start_of_month.year - 1)
            end_of_year_ago = end_of_month.replace(year=end_of_month.year - 1)
        except ValueError:
            # This happens if end_of_month is Feb 29th and the target year is not a leap year.
            # We safely default to Feb 28th for the historical end date in this case.
            start_of_year_ago = start_of_month.replace(year=start_of_month.year - 1)
            end_of_year_ago = date(end_of_month.year - 1, end_of_month.month, 28)

        # --- FIX: Stop iterating when the start date would be 2014 or earlier. ---
        if start_of_year_ago.year <= 2014:
            break

        # Calculate RPI for this specific month using the full period average
        rpi_value, excluded = calculate_rpi_period_average(
            basket,
            start_of_year_ago,
            end_of_year_ago,
            start_of_month,
            end_of_month,
            mapping_dict,
            show_progress=False # Always suppress progress bar for history calculation
        )

        # Stop if no RPI value could be calculated (means the data runs out)
        if rpi_value is None:
            break

        rpi_data.append({
            # Anchor the historical point to the last day of the month for plotting consistency
            'date': end_of_month,
            'rpi': rpi_value
        })

        # Move to the previous month (by setting day to 1, then subtracting one day)
        if current_date.month == 1:
            current_date = date(current_date.year - 1, 12, 1)
        else:
            current_date = date(current_date.year, current_date.month - 1, 1)

    df = pd.DataFrame(rpi_data)
    if not df.empty:
        df = df.set_index('date').sort_index()
        # FIX: Rename the 'rpi' column to 'YoY RPI (%)' to match the Streamlit line_chart call in Home.py
        df = df.rename(columns={'rpi': 'YoY RPI (%)'})
    return df

def calculate_rpi(basket, start_date, end_date, mapping_dict, show_progress=True):
    """
    Calculates the weighted RPI for a basket of goods using POINT-IN-TIME prices.
    'show_progress' controls whether a Streamlit progress bar is displayed.
    """

    valid_results = []
    excluded_items = []
    total_valid_weight = 0.0

    # We will use this to call the new average calculation, passing two identical date ranges
    # effectively making it a point-in-time calculation if we want to reuse the logic.
    # However, since we need distinct point-in-time logic, we stick to the original logic
    # but rename the function for clarity.

    if show_progress:
        progress_bar = st.progress(0, text="Initializing RPI calculation...")
    else:
        class DummyProgress:
            def progress(self, *args, **kwargs): pass
            def empty(self): pass
        progress_bar = DummyProgress()

    for i, (item_name, original_weight) in enumerate(basket.items()):
        if show_progress:
            progress_text = f"Calculating for '{item_name.lower()}' ({i+1}/{len(basket)})..."
            progress_bar.progress((i+1) / len(basket), text=progress_text)

        item_info = mapping_dict.get(item_name.lower())
        if not item_info:
            excluded_items.append(f"{item_name} (ID not found)")
            continue

        item_id = item_info['id']
        price_df = get_price_history(item_id)

        if price_df is None or price_df.empty:
            excluded_items.append(f"{item_name} (No price data from Wiki API)")
            continue

        # --- Use .asof() for point-in-time price (the original logic) ---
        old_price_data = price_df.asof(pd.to_datetime(start_date))
        new_price_data = price_df.asof(pd.to_datetime(end_date))

        # 4. Check if data exists for those dates
        if old_price_data is None or pd.isna(old_price_data['avgHighPrice']):
            excluded_items.append(f"{item_name} (Did not exist at start date: {start_date})")
            continue

        if new_price_data is None or pd.isna(new_price_data['avgHighPrice']):
            excluded_items.append(f"{item_name} (No data at end date: {end_date})")
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

    if total_valid_weight == 0:
        return None, excluded_items

    # --- Final RPI Calculation (Re-weighting) ---
    final_rpi = 0.0
    for item in valid_results:
        new_weight = item['original_weight'] / total_valid_weight
        weighted_contribution = item['inflation'] * new_weight
        final_rpi += weighted_contribution

    return final_rpi, excluded_items


def calculate_rpi_period_average(basket, start_old, end_old, start_new, end_new, mapping_dict, show_progress=True):
    """
    Calculates the weighted RPI for a basket of goods using the AVERAGE PRICE over two distinct periods.
    This is used for monthly RPI history.
    """

    valid_results = []
    excluded_items = []
    total_valid_weight = 0.0

    if show_progress:
        progress_bar = st.progress(0, text="Initializing Averaged RPI calculation...")
    else:
        class DummyProgress:
            def progress(self, *args, **kwargs): pass
            def empty(self): pass
        progress_bar = DummyProgress()

    for i, (item_name, original_weight) in enumerate(basket.items()):
        if show_progress:
            progress_text = f"Calculating average for '{item_name.lower()}' ({i+1}/{len(basket)})..."
            progress_bar.progress((i+1) / len(basket), text=progress_text)

        item_info = mapping_dict.get(item_name.lower())
        if not item_info:
            excluded_items.append(f"{item_name} (ID not found)")
            continue

        item_id = item_info['id']

        # 1. Get average price for the OLD period (one year ago)
        old_price = get_average_price_for_period(item_id, start_old, end_old)

        # 2. Get average price for the NEW period (the current month)
        new_price = get_average_price_for_period(item_id, start_new, end_new)

        # 3. Check for valid data
        if old_price is None or pd.isna(old_price) or old_price == 0:
            excluded_items.append(f"{item_name} (No average price data for old period: {start_old} to {end_old})")
            continue

        if new_price is None or pd.isna(new_price) or new_price == 0:
            excluded_items.append(f"{item_name} (No average price data for new period: {start_new} to {end_new})")
            continue

        # 4. Data is valid! Calculate item-specific inflation
        item_inflation = calculate_inflation_percent(old_price, new_price)

        valid_results.append({
            'name': item_name,
            'inflation': item_inflation,
            'original_weight': original_weight
        })
        total_valid_weight += original_weight

    if show_progress:
        progress_bar.empty()

    if total_valid_weight == 0:
        return None, excluded_items

    # --- Final RPI Calculation (Re-weighting) ---
    final_rpi = 0.0
    for item in valid_results:
        new_weight = item['original_weight'] / total_valid_weight
        weighted_contribution = item['inflation'] * new_weight
        final_rpi += weighted_contribution

    return final_rpi, excluded_items
