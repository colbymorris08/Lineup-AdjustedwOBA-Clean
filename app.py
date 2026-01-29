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
    from data_processor import LineupProtectionProcessor
    
    # Only load first 4 parts (March 28 - June 30, 2024)
    csv_parts = sorted(glob.glob("statcast_2024_part*.csv"))[:4]
    
    if not csv_parts:
        st.error("❌ No statcast CSV files found")
        st.stop()
    
    statcast_df = pd.concat([pd.read_csv(f, low_memory=False) for f in csv_parts], ignore_index=True)
    
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
        
        st.sidebar.divider()
        st.sidebar.caption("📅 Data: March 28 - June 30, 2024")
        st.sidebar.caption("⚾ ~350,000 pitches analyzed")

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
    
    st.markdown("""
    This tool isolates **true hitter talent** by removing context factors that inflate or suppress 
    traditional stats like wOBA. The core innovation is quantifying **lineup protection** — 
    the advantage hitters gain from the batters around them in the lineup.
    
    **The Theory:** 
    - A dangerous hitter **behind you** means pitchers can't pitch around you — they have to attack
    - A good hitter **in front of you** means more runners on base and pitchers working from the stretch
    
    Both factors lead to better pitches and more favorable hitting conditions.
    """)
    
    st.divider()
    
    # Key metrics row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Players Analyzed", len(df))
    with col2:
        st.metric("Date Range", "Mar-Jun 2024")
    with col3:
        pitches = df['total_pitches'].sum() if 'total_pitches' in df.columns else 350000
        st.metric("Pitches", f"{int(pitches):,}")
    with col4:
        st.metric("Adjustment Layers", "4")
    
    st.divider()
    
    # Quick findings
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔺 Most Context-Boosted")
        st.caption("These players benefited most from favorable conditions")
        if 'total_context_adj' in df.columns:
            overrated = df.nlargest(5, 'total_context_adj')[['Name', 'Team', 'wOBA', 'total_context_adj']].copy()
            overrated.columns = ['Player', 'Team', 'wOBA', 'Context Boost']
            st.dataframe(overrated.round(3), use_container_width=True, hide_index=True)
    
    with col2:
        st.subheader("🔻 Most Context-Suppressed")
        st.caption("These players performed despite unfavorable conditions")
        if 'total_context_adj' in df.columns:
            underrated = df.nsmallest(5, 'total_context_adj')[['Name', 'Team', 'wOBA', 'total_context_adj']].copy()
            underrated.columns = ['Player', 'Team', 'wOBA', 'Context Penalty']
            st.dataframe(underrated.round(3), use_container_width=True, hide_index=True)


def show_player_analysis(df, layers):
    st.header("👤 Player Analysis")

    player_names = sorted(df["Name"].dropna().unique())
    default_idx = player_names.index('Aaron Judge') if 'Aaron Judge' in player_names else 0
    selected = st.selectbox("Select Player", player_names, index=default_idx)

    player = df[df["Name"] == selected].iloc[0]

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader(player['Name'])
        st.caption(f"{player['Team']}")
        
        st.metric("Observed wOBA", f"{player['wOBA']:.3f}")
        diff = player['adjusted_wOBA'] - player['wOBA']
        st.metric(
            "Adjusted wOBA",
            f"{player['adjusted_wOBA']:.3f}",
            delta=f"{diff:+.3f}",
            delta_color="inverse"
        )
        
        st.divider()
        st.markdown("**Lineup Context**")
        
        ondeck = player.get('avg_ondeck_protection', 0)
        preceding = player.get('avg_preceding_protection', 0)
        lg_avg = df['wOBA'].mean()
        
        if pd.notna(ondeck):
            emoji_behind = "🟢" if ondeck > lg_avg else "🔴"
            st.caption(f"{emoji_behind} Hitter Behind: **{ondeck:.3f}** wOBA")
        if pd.notna(preceding):
            emoji_front = "🟢" if preceding > lg_avg else "🔴"
            st.caption(f"{emoji_front} Hitter In Front: **{preceding:.3f}** wOBA")
        
        st.caption(f"League Avg: {lg_avg:.3f}")

    with col2:
        # Waterfall with both protection factors
        x_labels = ["Observed"]
        y_values = [player["wOBA"]]
        measures = ["absolute"]
        
        if "Lineup Protection" in layers:
            ondeck_adj = player.get("ondeck_adj", 0) or 0
            preceding_adj = player.get("preceding_adj", 0) or 0
            x_labels.extend(["Behind", "In Front"])
            y_values.extend([-ondeck_adj, -preceding_adj])
            measures.extend(["relative", "relative"])
        
        if "Park Factors" in layers:
            x_labels.append("Park")
            y_values.append(-player.get("park_adj", 0))
            measures.append("relative")
            
        if "Pitcher Quality" in layers:
            x_labels.append("Pitchers")
            y_values.append(player.get("pitcher_adj", 0))
            measures.append("relative")
            
        if "Pitch Location" in layers:
            x_labels.append("Location")
            y_values.append(-player.get("pitch_quality_adj", 0))
            measures.append("relative")
        
        x_labels.append("Adjusted")
        y_values.append(0)
        measures.append("total")
        
        fig = go.Figure(go.Waterfall(
            x=x_labels,
            y=y_values,
            measure=measures,
            connector={"line": {"color": "gray"}},
            increasing={"marker": {"color": "#28a745"}},
            decreasing={"marker": {"color": "#dc3545"}},
            totals={"marker": {"color": "#007bff"}}
        ))
        fig.update_layout(title="wOBA Adjustment Waterfall", height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)


def show_leaderboards(df, layers):
    st.header("📊 Leaderboards")
    
    active_str = ', '.join(layers) if layers else "None"
    st.caption(f"**Active Layers:** {active_str}")
    
    lb_options = ["Adjusted wOBA", "Biggest Risers", "Biggest Fallers", "Best Protected", "Worst Protected"]
    lb_type = st.radio("Leaderboard", lb_options, horizontal=True)
    
    min_pa = st.slider("Minimum PA", 50, 300, 100)
    filtered = df[df['PA'] >= min_pa].copy() if 'PA' in df.columns else df.copy()
    
    if lb_type == "Adjusted wOBA":
        show_df = filtered.nlargest(25, 'adjusted_wOBA')[
            ['Name', 'Team', 'wOBA', 'adjusted_wOBA', 'total_selected_adj']
        ].copy()
        show_df.columns = ['Player', 'Team', 'Observed', 'Adjusted', 'Total Adj']
        
    elif lb_type == "Biggest Risers":
        show_df = filtered.nlargest(25, 'wOBA_diff')[
            ['Name', 'Team', 'wOBA', 'adjusted_wOBA', 'wOBA_diff']
        ].copy()
        show_df.columns = ['Player', 'Team', 'Observed', 'Adjusted', 'Change']
        
    elif lb_type == "Biggest Fallers":
        show_df = filtered.nsmallest(25, 'wOBA_diff')[
            ['Name', 'Team', 'wOBA', 'adjusted_wOBA', 'wOBA_diff']
        ].copy()
        show_df.columns = ['Player', 'Team', 'Observed', 'Adjusted', 'Change']
    
    elif lb_type == "Best Protected":
        if 'avg_ondeck_protection' in filtered.columns:
            filtered['combined_protection'] = (
                filtered['avg_ondeck_protection'].fillna(0) + 
                filtered['avg_preceding_protection'].fillna(0)
            ) / 2
            show_df = filtered.nlargest(25, 'combined_protection')[
                ['Name', 'Team', 'avg_ondeck_protection', 'avg_preceding_protection', 'wOBA']
            ].copy()
            show_df.columns = ['Player', 'Team', 'Behind', 'In Front', 'wOBA']
        else:
            show_df = filtered.nlargest(25, 'wOBA')[['Name', 'Team', 'wOBA']].copy()
            
    elif lb_type == "Worst Protected":
        if 'avg_ondeck_protection' in filtered.columns:
            filtered['combined_protection'] = (
                filtered['avg_ondeck_protection'].fillna(0) + 
                filtered['avg_preceding_protection'].fillna(0)
            ) / 2
            show_df = filtered.nsmallest(25, 'combined_protection')[
                ['Name', 'Team', 'avg_ondeck_protection', 'avg_preceding_protection', 'wOBA']
            ].copy()
            show_df.columns = ['Player', 'Team', 'Behind', 'In Front', 'wOBA']
        else:
            show_df = filtered.nsmallest(25, 'wOBA')[['Name', 'Team', 'wOBA']].copy()
    
    st.dataframe(show_df.round(3), use_container_width=True, hide_index=True)


def show_methodology():
    st.header("🔬 Methodology")
    
    st.markdown("""
    ## Lineup Protection: The Core Innovation
    
    Traditional stats treat all plate appearances equally. But a hitter's context matters:
    
    ### 🔜 Hitter Behind (On-Deck Protection)
    
    When a dangerous hitter bats behind you, pitchers face a dilemma:
    
    | Option | Risk |
    |--------|------|
    | Pitch around you | Walk you, still face the dangerous hitter |
    | Attack you | Give you hittable pitches |
    
    **Result:** Protected hitters see better pitches → inflated stats
    
    **Example:** Juan Soto with Aaron Judge behind him sees far better pitches than 
    a hitter with a weak bat on deck.
    
    ---
    
    ### 🔙 Hitter In Front (Preceding Protection)
    
    When a good hitter bats in front of you:
    - More runners on base when you come up
    - Pitchers working from the stretch (harder to control)
    - More pressure situations = pitcher mistakes
    - Better RBI opportunities
    
    ---
    
    ### Combined Protection Score
    
    We calculate protection from both directions:
```
    Total Protection Adj = (Behind Adj) + (In Front Adj)
```
    
    Each uses the season wOBA of the surrounding hitters compared to league average.
    
    ---
    
    ## Other Adjustment Layers
    
    **Park Factors**
    - FanGraphs 5-year park factors
    - Coors Field: +13% | T-Mobile Park: -6%
    
    **Pitcher Quality Faced**
    - Average opponent FIP- across all plate appearances
    - Below 100 = faced tougher pitching
    
    **Pitch Location Quality**
    - Percentage of pitches in the "heart" of the zone
    - Inner third of strike zone = most hittable
    
    ---
    
    ## Data Sources
    
    | Source | Data | Coverage |
    |--------|------|----------|
    | Baseball Savant | Pitch-by-pitch Statcast | Mar 28 - Jun 30, 2024 |
    | FanGraphs | Batting & pitching stats | 2024 season |
    | FanGraphs | Park factors | 5-year average |
    """)


def show_visualizations(df, layers):
    st.header("📈 Visualizations")
    
    viz = st.selectbox("Select Visualization", [
        "Observed vs Adjusted Scatter",
        "Protection Score Distribution",
        "Context Adjustment by Team"
    ])
    
    if viz == "Observed vs Adjusted Scatter":
        fig = px.scatter(
            df,
            x="wOBA",
            y="adjusted_wOBA",
            hover_name="Name",
            hover_data=["Team"],
            color="total_selected_adj",
            color_continuous_scale="RdYlGn_r",
            title="Observed vs Adjusted wOBA"
        )
        fig.add_trace(go.Scatter(
            x=[.250, .450], y=[.250, .450],
            mode='lines',
            line=dict(dash='dash', color='gray'),
            showlegend=False
        ))
        fig.update_layout(height=600)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Points above the line = underrated | Points below = overrated")
        
    elif viz == "Protection Score Distribution":
        if 'avg_ondeck_protection' in df.columns:
            col1, col2 = st.columns(2)
            with col1:
                fig1 = px.histogram(df, x='avg_ondeck_protection', nbins=25, 
                                    title='Hitter Behind (On-Deck) Protection')
                fig1.add_vline(x=df['avg_ondeck_protection'].mean(), line_dash="dash", 
                              line_color="red", annotation_text="Avg")
                st.plotly_chart(fig1, use_container_width=True)
            with col2:
                fig2 = px.histogram(df, x='avg_preceding_protection', nbins=25,
                                    title='Hitter In Front Protection')
                fig2.add_vline(x=df['avg_preceding_protection'].mean(), line_dash="dash",
                              line_color="red", annotation_text="Avg")
                st.plotly_chart(fig2, use_container_width=True)
        else:
            st.warning("Protection data not available")
            
    elif viz == "Context Adjustment by Team":
        if 'total_context_adj' in df.columns:
            team_adj = df.groupby('Team')['total_context_adj'].mean().sort_values()
            fig = px.bar(
                x=team_adj.values,
                y=team_adj.index,
                orientation='h',
                title='Average Context Adjustment by Team',
                labels={'x': 'Avg Context Adjustment', 'y': 'Team'}
            )
            fig.update_layout(height=700)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Context adjustment data not available")


# =========================
# ENTRY POINT
# =========================
if __name__ == "__main__":
    main()
