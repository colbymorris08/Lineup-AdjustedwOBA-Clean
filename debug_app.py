# debug_app.py

import streamlit as st
import traceback

st.set_page_config(page_title="Debug Mode – Lineup wOBA", layout="wide")

st.title("🛠️ Debugging Lineup-Adjusted wOBA App")

try:
    st.write("Step 1: Trying to import helper modules...")
    from data_loader import load_all_data
    st.success("✅ Imported `data_loader`")

    from data_processing import build_full_dataset
    st.success("✅ Imported `data_processing`")

    st.write("Step 2: Loading raw CSVs...")
    raw_dfs = load_all_data()
    st.success("✅ Raw data loaded")

    st.write("Step 3: Building full dataset...")
    df, layers = build_full_dataset(raw_dfs)
    st.success("✅ Dataset built")

    st.write("Step 4: Displaying preview...")
    st.dataframe(df.head(5))

except Exception as e:
    st.error("🚨 An error occurred while running the debug app:")
    st.code(traceback.format_exc())
