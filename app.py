"""
Lineup Protection Projection Tool
MLB Interview Project

Evaluates hitters by projecting performance against league-average pitch quality,
controlling for lineup protection and context factors.
"""

import streamlit as st
import traceback
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import glob

# =========================
# PAGE CONFIG
# =========================
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
    """Load all datasets and build full adjusted dataset."""

    csv_parts = sorted(glob.glob("statcast_2024_part*.csv"))
    if not csv_parts:
        st.error("❌ No statcast CSV chunks found")
        st.stop()

    try:
        statcast_df = pd.concat(
            (pd.read_csv(f, low_memory=False) for f in csv_parts),
            ignore_index=True
        )
    except Exception as e:
        st.error("❌ Failed to read Statcast CSV parts")
        st.code(str(e))
        st.stop()

    # Required Statcast fields
    required_cols = ["plate_x", "plate_z"]
    missing = [c for c in required_cols if c not in statcast_df.columns]
    if missing:
        st.error(f"❌ Missing required Statcast columns: {', '.join(missing)}")
        st.stop()

    from data_processor import LineupProtectionProcessor

    processor = LineupProtectionProcessor(".")
    processor.statcast = statcast_df
    processor.load_all_data()

    df = processor.build_full_dataset()
    return df, processor

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

        # Sidebar
        st.sidebar.title("Navigation")
        page = st.sidebar.radio(
            "Select View",
            ["🏠 Overview", "👤 Player Analysis", "📊 Leaderboards", "🔬 Methodology", "📈 Visualizations"]
        )

        st.sidebar.divider()
        st.sidebar.subheader("🎚️ Adjustment Layers")

        layers = []
        if st.sidebar.checkbox("Lineup Protection", value=True):
            layers.append("Lineup Protection")
        if st.sidebar.checkbox("Park Factors", value=True):
            layers.append("Park Factors")
        if st.sidebar.checkbox("Pitcher Quality", value=True):
            layers.append("Pitcher Quality")
        if st.sidebar.checkbox("Pitch Location", value=True):
            layers.append("Pitch Location")

        st.sidebar.caption(f"**{len(layers)} layer(s) active**")

        with st.spinner("Loading data..."):
            df, processor = load_data()
            df = calculate_adjusted_woba(df, layers)
            st.sidebar.success(f"✅ {len(df)} players loaded")

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
        st.error("🚨 A fatal error occurred")
        st.code(traceback.format_exc())

# =========================
# VIEWS
# =========================
def show_overview(df, layers):
    st.header("Project Overview")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("""
        ### Why This Matters
        Traditional batting stats reflect outcomes, not *conditions*.

        This tool removes:
        - Lineup protection
        - Park inflation
        - Pitcher quality bias
        - Pitch location quality

        to estimate **true hitter talent**.
        """)

    with col2:
        st.metric("Players", len(df))
        st.metric("Season", "2024")

def show_player_analysis(df, layers):
    st.header("👤 Player Analysis")

    player_names = sorted(df["Name"].dropna().unique())
    selected = st.selectbox("Select Player", player_names)

    player = df[df["Name"] == selected].iloc[0]

    col1, col2 = st.columns([1, 2])

    with col1:
        st.metric("Observed wOBA", f"{player['wOBA']:.3f}")
        st.metric(
            "Adjusted wOBA",
            f"{player['adjusted_wOBA']:.3f}",
            delta=f"{player['adjusted_wOBA'] - player['wOBA']:+.3f}",
            delta_color="inverse"
        )

    with col2:
        fig = go.Figure(go.Waterfall(
            x=["Observed", "Protection", "Park", "Pitchers", "Location", "Adjusted"],
            y=[
                player["wOBA"],
                -player.get("protection_adj", 0),
                -player.get("park_adj", 0),
                player.get("pitcher_adj", 0),
                -player.get("pitch_quality_adj", 0),
                0
            ],
            measure=["absolute", "relative", "relative", "relative", "relative", "total"]
        ))
        st.plotly_chart(fig, use_container_width=True)

def show_leaderboards(df, layers):
    st.header("📊 Leaderboards")
    st.dataframe(
        df.sort_values("adjusted_wOBA", ascending=False)[
            ["Name", "Team", "wOBA", "adjusted_wOBA", "total_selected_adj"]
        ].head(25),
        use_container_width=True
    )

def show_methodology():
    st.header("🔬 Methodology")
    st.markdown("""
    **Lineup Protection**
    - Uses on‑deck hitter season wOBA
    - Converts protection advantage → pitch quality → wOBA boost

    **Park Factors**
    - FanGraphs 5‑year park factors

    **Pitcher Quality**
    - Opponent FIP‑ faced

    **Pitch Location**
    - Heart‑zone frequency
    """)

def show_visualizations(df, layers):
    st.header("📈 Visualizations")
    fig = px.scatter(
        df,
        x="wOBA",
        y="adjusted_wOBA",
        hover_name="Name",
        title="Observed vs Adjusted wOBA"
    )
    st.plotly_chart(fig, use_container_width=True)

# =========================
# ENTRY POINT
# =========================
if __name__ == "__main__":
    main()
