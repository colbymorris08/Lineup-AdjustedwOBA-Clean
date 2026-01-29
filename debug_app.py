"""
DEBUG VERSION — Lineup Protection Projection Tool
This file exists ONLY to surface hidden Streamlit Cloud errors.
"""

import streamlit as st
import traceback
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import glob
import os
import psutil
from datetime import datetime

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="DEBUG — Lineup Protection Projection Tool",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🛠️ DEBUG MODE — Lineup Protection Projection Tool")
st.caption("This version logs *everything* so we can see where Streamlit Cloud crashes.")

# =========================
# HELPER: MEMORY STATUS
# =========================
def memory_status():
    mem = psutil.virtual_memory()
    return f"{mem.percent}% used ({mem.used / 1e9:.2f} GB / {mem.total / 1e9:.2f} GB)"

st.sidebar.markdown("### 🧠 Memory Status")
st.sidebar.code(memory_status())

# =========================
# STEP LOGGER
# =========================
def log_step(msg):
    st.write(f"✅ {msg}")
    st.caption(datetime.utcnow().strftime("%H:%M:%S UTC"))

# =========================
# DATA LOADING
# =========================
@st.cache_data(ttl=3600)
def load_data_debug():
    try:
        log_step("Entered load_data_debug()")

        # ---- Find Statcast files
        csv_parts = sorted(glob.glob("statcast_2024_part*.csv"))
        st.write("📄 Found Statcast files:", csv_parts)

        if not csv_parts:
            st.error("❌ No statcast_2024_part*.csv files found")
            st.stop()

        dfs = []
        total_rows = 0

        for f in csv_parts:
            try:
                st.write(f"📥 Reading {f}")
                df_part = pd.read_csv(f, low_memory=False)
                st.write(f"   → {len(df_part):,} rows")
                total_rows += len(df_part)
                dfs.append(df_part)
            except Exception:
                st.error(f"❌ Failed reading {f}")
                st.code(traceback.format_exc())
                st.stop()

        st.success(f"✅ Loaded {total_rows:,} Statcast rows total")

        statcast_df = pd.concat(dfs, ignore_index=True)

        log_step("Statcast concatenation successful")
        st.write("📊 Statcast shape:", statcast_df.shape)

        # ---- Validate columns
        required_cols = ["plate_x", "plate_z"]
        missing = [c for c in required_cols if c not in statcast_df.columns]
        if missing:
            st.error(f"❌ Missing required Statcast columns: {missing}")
            st.stop()

        log_step("Required Statcast columns validated")

        # ---- Import processor
        try:
            from data_processor import LineupProtectionProcessor
            log_step("Imported LineupProtectionProcessor")
        except Exception:
            st.error("❌ Failed importing LineupProtectionProcessor")
            st.code(traceback.format_exc())
            st.stop()

        # ---- Initialize processor
        try:
            processor = LineupProtectionProcessor(".")
            processor.statcast = statcast_df
            log_step("Processor initialized and statcast assigned")
        except Exception:
            st.error("❌ Processor initialization failed")
            st.code(traceback.format_exc())
            st.stop()

        # ---- Load auxiliary datasets
        try:
            log_step("Calling processor.load_all_data()")
            processor.load_all_data()
        except Exception:
            st.error("❌ processor.load_all_data() crashed")
            st.code(traceback.format_exc())
            st.stop()

        # ---- Build full dataset
        try:
            log_step("Calling processor.build_full_dataset()")
            df = processor.build_full_dataset()
            st.success(f"✅ build_full_dataset() returned {len(df):,} rows")
        except Exception:
            st.error("❌ processor.build_full_dataset() crashed")
            st.code(traceback.format_exc())
            st.stop()

        st.sidebar.success("✅ Data fully loaded")
        return df, processor

    except Exception:
        st.error("🚨 UNHANDLED ERROR IN load_data_debug()")
        st.code(traceback.format_exc())
        st.stop()

# =========================
# ADJUSTMENT LOGIC
# =========================
def calculate_adjusted_woba(df, layers):
    log_step("Calculating adjusted wOBA")
    df = df.copy()

    df["adjusted_wOBA"] = df["wOBA"]
    df["total_selected_adj"] = 0.0

    if "Lineup Protection" in layers:
        df["adjusted_wOBA"] -= df["protection_adj"].fillna(0)
        df["total_selected_adj"] += df["protection_adj"].fillna(0)

    if "Park Factors" in layers:
        df["adjusted_wOBA"] -= df["park_adj"].fillna(0)
        df["total_selected_adj"] += df["park_adj"].fillna(0)

    if "Pitcher Quality" in layers:
        df["adjusted_wOBA"] += df["pitcher_adj"].fillna(0)
        df["total_selected_adj"] -= df["pitcher_adj"].fillna(0)

    if "Pitch Location" in layers:
        df["adjusted_wOBA"] -= df["pitch_quality_adj"].fillna(0)
        df["total_selected_adj"] += df["pitch_quality_adj"].fillna(0)

    df["wOBA_diff"] = df["adjusted_wOBA"] - df["wOBA"]
    return df

# =========================
# MAIN
# =========================
def main():
    try:
        log_step("Entered main()")

        st.sidebar.title("Navigation")
        page = st.sidebar.radio(
            "Select View",
            ["Overview", "Player Analysis", "Leaderboards"]
        )

        layers = []
        if st.sidebar.checkbox("Lineup Protection", True):
            layers.append("Lineup Protection")
        if st.sidebar.checkbox("Park Factors", True):
            layers.append("Park Factors")
        if st.sidebar.checkbox("Pitcher Quality", True):
            layers.append("Pitcher Quality")
        if st.sidebar.checkbox("Pitch Location", True):
            layers.append("Pitch Location")

        st.sidebar.caption(f"{len(layers)} layers active")

        with st.spinner("🔄 Loading data (DEBUG)..."):
            df, processor = load_data_debug()
            df = calculate_adjusted_woba(df, layers)

        st.success("🎉 App fully initialized without crashing")

        if page == "Overview":
            st.header("Overview")
            st.write(df.head())

        elif page == "Player Analysis":
            st.header("Player Analysis")
            player = st.selectbox("Player", sorted(df["Name"].dropna().unique()))
            st.write(df[df["Name"] == player])

        elif page == "Leaderboards":
            st.header("Leaderboards")
            st.dataframe(
                df.sort_values("adjusted_wOBA", ascending=False)
                [["Name", "Team", "wOBA", "adjusted_wOBA"]]
                .head(25)
            )

    except Exception:
        st.error("🚨 FATAL ERROR IN main()")
        st.code(traceback.format_exc())

# =========================
# ENTRY POINT
# =========================
if __name__ == "__main__":
    main()
