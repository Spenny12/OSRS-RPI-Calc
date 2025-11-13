import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Import your custom modules
from api_client import get_item_mapping, get_price_history, find_item_id
from calculator import get_item_price_on_date, calculate_inflation, calculate_rpi

st.set_page_config(
    page_title="Custom Inflation Calculator",
    page_icon="🛠️",
    layout="wide"
)

st.title("🛠️ Custom Inflation Calculator")

# --- Load Mapping Data ---
# This is needed for all calculators on this page
mapping = get_item_mapping()
if not mapping:
    st.error("Failed to load OSRS item database. Cannot proceed.", icon="🚨")
    st.stop() # Stop execution of this page

# Get a clean list of item names for selectboxes
item_names_list = sorted([item['name'] for item in mapping if 'name' in item])


# --- Mode Selection ---
calc_mode = st.radio(
    "Select Calculator Mode:",
    ("Single Item", "Custom RPI Basket"),
    horizontal=True,
    key="calc_mode"
)

# --- Shared Date Inputs ---
st.markdown("---")
st.subheader("1. Select Timeframe")
calc_type = st.radio(
    "Select Timeframe:",
    ("Default (Last Year)", "Custom Date Range", "Custom Duration from Today"),
    horizontal=True,
    key="calc_timeframe"
)

today = datetime.now().date()
start_date = None
end_date = today

if calc_type == "Default (Last Year)":
    start_date = today - timedelta(days=365)
elif calc_type == "Custom Date Range":
    col_date1, col_date2 = st.columns(2)
    with col_date1:
        start_date = st.date_input("Start Date", value=today - timedelta(days=365))
    with col_date2:
        end_date = st.date_input("End Date", value=today)
elif calc_type == "Custom Duration from Today":
    days_ago = st.number_input(
        "Select Timeframe (Days Ago):", 
        min_value=1, 
        value=365,
        help="Calculate from this many days ago to today."
    )
    start_date = today - timedelta(days=days_ago)


# ==============================================================================
# --- SINGLE ITEM CALCULATOR ---
# ==============================================================================
if calc_mode == "Single Item":
    st.markdown("---")
    st.subheader("2. Select Item")
    
    col_item, col_btn = st.columns([4, 1])
    with col_item:
        item_name = st.selectbox("Select an OSRS Item:", options=item_names_list, index=item_names_list.index("Shark"))
    
    with col_btn:
        st.write(" ") # Spacer
        run_single_calc = st.button("Calculate", type="primary", use_container_width=True, key="run_single")

    if run_single_calc:
        if start_date >= end_date:
            st.error("Start date must be before the end date.")
        else:
            item_id = find_item_id(item_name, mapping)
            if not item_id:
                st.error(f"Could not find ID for '{item_name}'.")
            else:
                with st.spinner(f"Fetching price history for {item_name}..."):
                    price_df = get_price_history(item_id)
                
                old_price_data = get_item_price_on_date(price_df, start_date)
                new_price_data = get_item_price_on_date(price_df, end_date)

                # --- Validation ---
                if old_price_data is None:
                    st.error(f"No price data found for '{item_name}' on or before {start_date}. The item may not have existed.", icon="⚠️")
                elif new_price_data is None:
                    st.error(f"No price data found for '{item_name}' on or before {end_date}.", icon="⚠️")
                else:
                    # --- Calculation & Display ---
                    inflation_rate = calculate_inflation(old_price_data['price'], new_price_data['price'])
                    
                    st.markdown("---")
                    st.subheader(f"Results for: {item_name}")
                    
                    st.metric(
                        label=f"Inflation Rate ({old_price_data['actual_date']} to {new_price_data['actual_date']})",
                        value=f"{inflation_rate:.2f}%"
                    )
                    
                    res_col1, res_col2 = st.columns(2)
                    with res_col1:
                        st.metric(label=f"Price on {old_price_data['actual_date']}", value=f"{int(old_price_data['price']):,} gp")
                    with res_col2:
                        st.metric(label=f"Price on {new_price_data['actual_date']}", value=f"{int(new_price_data['price']):,} gp")
                
                    st.subheader("Price History Chart")
                    chart_df = price_df[(price_df.index >= pd.to_datetime(start_date)) & 
                                        (price_df.index <= pd.to_datetime(end_date))]
                    st.line_chart(chart_df['avgHighPrice'])


# ==============================================================================
# --- CUSTOM RPI BASKET CALCULATOR ---
# ==============================================================================
elif calc_mode == "Custom RPI Basket":
    st.markdown("---")
    st.subheader("2. Build Your Basket")
    
    # Initialize session state for the basket
    if "custom_basket_items" not in st.session_state:
        st.session_state.custom_basket_items = ["Shark", "Prayer potion(4)"]

    # --- Item Selection ---
    st.session_state.custom_basket_items = st.multiselect(
        "Select items for your basket:",
        options=item_names_list,
        default=st.session_state.custom_basket_items,
        key="basket_multiselect"
    )
    
    # --- Weight Assignment ---
    final_basket = {} # This will hold {item_name: weight}
    
    if not st.session_state.custom_basket_items:
        st.warning("Please add at least one item to your basket.")
    else:
        st.markdown("##### Assign Weights")
        st.info("Assign a 'weight' to each item. A weight of 2 is twice as important as 1. The app will normalize these automatically.")
        
        total_weight = 0
        cols = st.columns(len(st.session_state.custom_basket_items))
        
        for i, item_name in enumerate(st.session_state.custom_basket_items):
            with cols[i]:
                # Use item name in key to ensure widget is unique
                weight = st.number_input(f"{item_name}", min_value=1, value=1, key=f"weight_{item_name}")
                final_basket[item_name] = weight
                total_weight += weight
        
        # Normalize weights for the calculator
        if total_weight > 0:
            normalized_basket = {item: (weight / total_weight) for item, weight in final_basket.items()}
            
            st.markdown("---")
            run_rpi_calc = st.button("Calculate RPI", type="primary", use_container_width=True, key="run_rpi")
            
            if run_rpi_calc:
                if start_date >= end_date:
                    st.error("Start date must be before the end date.")
                else:
                    with st.spinner("Calculating custom RPI..."):
                        rpi_value, excluded = calculate_rpi(normalized_basket, start_date, end_date, mapping)
                    
                    st.markdown("---")
                    st.subheader("Custom RPI Result")
                    
                    if rpi_value is not None:
                        st.metric(
                            label=f"Weighted Inflation ({start_date} to {end_date})",
                            value=f"{rpi_value:.2f}%"
                        )
                        
                        with st.expander("See your basket composition (normalized)"):
                            st.json({k: f"{v*100:.2f}% weight" for k, v in normalized_basket.items()})

                        if excluded:
                            st.warning(f"Some items were excluded from this calculation: {', '.join(excluded)}")
                    else:
                        st.error("Could not calculate RPI. No valid data was found for any item in your basket for this period.")
