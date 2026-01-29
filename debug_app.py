import streamlit as st
import traceback
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import glob
import os

st.set_page_config(
    page_title="Lineup Protection Projection Tool",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================
# DATA LOADING
# =========================
@st.cache_data(ttl=3600)
def load_data():
    """Load and process Statcast chunks with extensive error handling."""
    try:
        csv_files = sorted(glob.glob("statcast_2024_part*.csv"))
        if not csv_files:
            raise FileNotFoundError("No files found matching statcast_2024_part*.csv in directory.")

        dfs = []
        for f in csv_files:
            try:
                dfs.append(pd.read_csv(f, low_memory=False))
            except Exception as e:
                raise RuntimeError(f"Failed to load {f}: {str(e)}")

        statcast = pd.concat(dfs, ignore_index=True)

        required = ["plate_x", "plate_z"]
        missing = [col for col in required if col not in statcast.columns]
        if missing:
            raise KeyError(f"Missing required Statcast columns: {', '.join(missing)}")

        # Import processor
        try:
            from data_processor import LineupProtectionProcessor
        except Exception as e:
            raise ImportError(f"Error importing LineupProtectionProcessor: {str(e)}")

        processor = LineupProtectionProcessor(".")
        processor.statcast = statcast

        try:
            processor.load_all_data()
        except Exception as e:
            raise RuntimeError(f"load_all_data() failed: {str(e)}")

        try:
            df = processor.build_full_dataset()
        except Exception as e:
            raise RuntimeError(f"build_full_dataset() failed: {str(e)}")

        return df, processor

    except Exception as e:
        st.error("🚨 Failed to load and process data.")
        st.code(traceback.format_exc())
        st.stop()


# =========================
# ADJUSTMENT LOGIC
# =========================
def calculate_adjusted_woba(df: pd.DataFrame, layers: list) -> pd.DataFrame:
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
# MAIN APP
# =========================
def main():
    try:
        st.title("⚾ Lineup Protection Projection Tool")
        st.markdown("*Isolating true hitter talent by controlling for context factors*")

        page = st.sidebar.radio(
            "Select View",
            ["🏠 Overview", "👤 Player Analysis", "📊 Leaderboards", "🔬 Methodology", "📈 Visualizations"]
        )

        st.sidebar.divider()
        st.sidebar.subheader("🎚️ Adjustment Layers")

        layers = []
        if st.sidebar.checkbox("Lineup Protection", value=True): layers.append("Lineup Protection")
        if st.sidebar.checkbox("Park Factors", value=True): layers.append("Park Factors")
        if st.sidebar.checkbox("Pitcher Quality", value=True): layers.append("Pitcher Quality")
        if st.sidebar.checkbox("Pitch Location", value=True): layers.append("Pitch Location")

        with st.spinner("🔄 Loading data and applying adjustments..."):
            df, processor = load_data()
            df = calculate_adjusted_woba(df, layers)

        if page == "🏠 Overview":
            show_overview(df, layers)
        elif page == "👤 Player Analysis":
            show_player_analysis(df, layers)
        elif page == "📊 Leaderboards":
            show_leaderboards(df, layers)
        elif page == "🔬 Methodology":
            show_methodology()
        elif page == "📈 Visualizations":
            show_visualizations(df, layers)

    except Exception:
        st.error("🚨 A fatal error occurred.")
        st.code(traceback.format_exc())


# =========================
# VIEW FUNCTIONS
# =========================
def show_overview(df, layers):
    st.header("🏠 Project Overview")
    st.write("This tool controls for external biasing factors like lineup protection, parks, and pitch quality.")
    st.metric("Total Players", len(df))

def show_player_analysis(df, layers):
    st.header("👤 Player Analysis")
    player_names = sorted(df["Name"].dropna().unique())
    selected = st.selectbox("Select Player", player_names)
    player = df[df["Name"] == selected].iloc[0]

    st.metric("Observed wOBA", f"{player['wOBA']:.3f}")
    st.metric("Adjusted wOBA", f"{player['adjusted_wOBA']:.3f}", delta=f"{player['wOBA_diff']:+.3f}")

def show_leaderboards(df, layers):
    st.header("📊 Adjusted wOBA Leaderboard")
    st.dataframe(
        df.sort_values("adjusted_wOBA", ascending=False)[
            ["Name", "Team", "wOBA", "adjusted_wOBA", "total_selected_adj"]
        ].head(25),
        use_container_width=True
    )

def show_methodology():
    st.header("🔬 Methodology")
    st.markdown("Explains how lineup protection and other effects are quantified and adjusted.")

def show_visualizations(df, layers):
    st.header("📈 Observed vs Adjusted wOBA")
    fig = px.scatter(
        df,
        x="wOBA",
        y="adjusted_wOBA",
        hover_name="Name",
        title="Observed vs Adjusted wOBA"
    )
    st.plotly_chart(fig, use_container_width=True)

# =========================
# ENTRY
# =========================
if __name__ == "__main__":
    main()
