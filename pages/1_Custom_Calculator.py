import streamlit as st
from datetime import datetime, timedelta
from api_client import get_item_mapping
from calculator import calculate_single_item_inflation, calculate_rpi
import pandas as pd

st.set_page_config(page_title="Custom Calculator", page_icon="🎛️", layout="wide")
st.title("🎛️ Custom Inflation Calculator")

# --- Load Mapping Data ---
# CRITICAL: Caching is DISABLED for debugging
# @st.cache_resource
def load_mapping_data():
    return get_item_mapping()

mapping_dict, item_names_list = load_mapping_data()

if not mapping_dict or not item_names_list:
    st.error("Failed to load OSRS item database. The API might be down. Please try again later.")
    st.stop()


# --- UI Configuration ---
col1, col2 = st.columns([1, 2]) # Ratio for inputs vs. results

with col1:
    st.subheader("1. Select Calculation Mode")
    mode = st.radio(
        "Mode:",
        ("Single Item", "Custom RPI Basket"),
        horizontal=True,
        label_visibility="collapsed"
    )

    st.subheader("2. Select Timeframe")
    today = datetime.now().date()
    start_date = st.date_input("Start Date", value=today - timedelta(days=365))
    end_date = st.date_input("End Date", value=today)

    # --- Mode-Specific UI ---
    if mode == "Single Item":
        st.subheader("3. Select Item")
        # Ensure 'shark' is a valid key, otherwise default to first item
        default_index = 0
        if "Shark" in item_names_list:
            default_index = item_names_list.index("Shark")

        item_name = st.selectbox(
            "Item Name:",
            options=item_names_list,
            index=default_index
        )

        if st.button("Calculate Single Item Inflation", type="primary", use_container_width=True):
            if start_date >= end_date:
                st.error("Start date must be before the end date.")
            else:
                with col2:
                    st.subheader(f"Results for: {item_name.title()}")
                    with st.spinner(f"Fetching price history for {item_name}..."):

                        # --- Run Single Item Calculation ---
                        result = calculate_single_item_inflation(
                            item_name,
                            start_date,
                            end_date,
                            mapping_dict
                        )

                        if result.get('error'):
                            st.error(result['error'])
                        else:
                            # --- Display Single Item Results ---
                            st.metric(
                                label=f"Inflation Rate ({result['actual_start_date']} to {result['actual_end_date']})",
                                value=f"{result['inflation_rate']:.2f}%"
                            )
                            st.markdown("---")
                            res_col1, res_col2 = st.columns(2)
                            with res_col1:
                                st.metric(label=f"Price on {result['actual_start_date']}", value=f"{int(result['old_price']):,} gp")
                            with res_col2:
                                st.metric(label=f"Price on {result['actual_end_date']}", value=f"{int(result['new_price']):,} gp")

                            st.subheader("Price History Chart")
                            chart_df = result['price_df']
                            chart_df = chart_df[chart_df.index >= pd.to_datetime(start_date)]
                            chart_df = chart_df[chart_df.index <= pd.to_datetime(end_date)]
                            st.line_chart(chart_df['avgHighPrice'])

                        # --- NEW: DEBUGGER UI ---
                        st.markdown("---")
                        with st.expander("Show Debug Information (Click to open)"):
                            debug_data = result.get('debug_info', {})

                            st.text_input("Queried URL (cURL):", value=debug_data.get('url', 'N/A'), disabled=True)

                            status_code = debug_data.get('status_code')
                            st.metric("API Status Code:", value=str(status_code) if status_code else "N/A")

                            response_text = debug_data.get('response_text', '')

                            st.download_button(
                                label="Download API Response",
                                data=response_text,
                                file_name=f"api_response_{item_name}.json" if (response_text and response_text.strip().startswith('{')) else f"api_response_{item_name}.txt",
                                mime="application/json" if (response_text and response_text.strip().startswith('{')) else "text/plain"
                            )

                            st.text_area("Raw API Response:", value=response_text or "No response text captured.", height=300)

                            if debug_data.get('error'):
                                st.error(f"Processing Error: {debug_data['error']}")

    elif mode == "Custom RPI Basket":
        st.subheader("3. Build Custom Basket")
        st.markdown("Add items and their weight. All weights will be normalized (e.g., 2 and 3 become 40% and 60%).")

        if 'custom_basket' not in st.session_state:
            st.session_state.custom_basket = {}

        # --- UI for adding items to the basket ---
        form_col1, form_col2, form_col3 = st.columns([3, 1, 1])

        # Ensure 'Shark' is a valid key, otherwise default to first item
        default_index = 0
        if "Shark" in item_names_list:
            default_index = item_names_list.index("Shark")

        with form_col1:
            new_item_name = st.selectbox(
                "Item Name:",
                options=item_names_list,
                index=default_index,
                key="basket_item_name"
            )
        with form_col2:
            new_item_weight = st.number_input("Weight", min_value=1, value=1, key="basket_item_weight")

        with form_col3:
            st.markdown("##") # Spacer
            if st.button("Add", use_container_width=True):
                if new_item_name in st.session_state.custom_basket:
                    st.warning(f"'{new_item_name}' is already in the basket. Use 'Remove' to change it.")
                else:
                    st.session_state.custom_basket[new_item_name] = new_item_weight
                    st.rerun()

        # --- Display the basket ---
        if st.session_state.custom_basket:
            st.markdown("---")
            total_weight = sum(st.session_state.custom_basket.values())

            for item, weight in st.session_state.custom_basket.items():
                item_col1, item_col2, item_col3 = st.columns([4, 2, 1])
                with item_col1:
                    st.markdown(f"**{item.title()}**")
                with item_col2:
                    st.markdown(f"Weight: {weight} (`{weight/total_weight*100:.1f}%`)")
                with item_col3:
                    if st.button(f"Remove##{item}", use_container_width=True, key=f"del_{item}"):
                        del st.session_state.custom_basket[item]
                        st.rerun()

            st.markdown("---")
            if st.button("Calculate Custom RPI", type="primary", use_container_width=True):
                if start_date >= end_date:
                    st.error("Start date must be before the end date.")
                else:
                    with col2:
                        st.subheader("Custom RPI Results")

                        # --- Run RPI Calculation ---
                        rpi_value, excluded = calculate_rpi(
                            st.session_state.custom_basket,
                            start_date,
                            end_date,
                            mapping_dict
                        )

                        if rpi_value is not None:
                            st.metric(
                                label=f"Weighted Inflation ({start_date} to {end_date})",
                                value=f"{rpi_value:.2f}%"
                            )
                            if excluded:
                                st.warning("Some items were excluded:")
                                for item in excluded:
                                    st.markdown(f"- {item}")
                        else:
                            st.error("Could not calculate RPI. No valid data was found for any item in the basket.")
                            if excluded:
                                st.subheader("Reasons for failure:")
                                for item in excluded:
                                    st.markdown(f"- {item}")
