"""
Lineup Protection Projection Tool
MLB Interview Project

Evaluates hitters by projecting performance against league-average pitch quality,
controlling for lineup protection and context factors.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
import lzma

st.write("✅ App started")

csv_parts = sorted(glob.glob("statcast_2024_part*.csv"))
st.write(f"📄 Found CSV parts: {csv_parts}")

try:
    df = pd.concat([pd.read_csv(f) for f in csv_parts])
    st.write("✅ Data loaded successfully")
except Exception as e:
    st.error(f"❌ Failed to load data: {e}")
    raise

# =========================
# LOCAL DATA CONFIG
# =========================


st.set_page_config(
    page_title="Lineup Protection Projection Tool",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="expanded"
)
@st.cache_data(ttl=3600)
def load_data():
    """Load and process all data."""

    import glob

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
        st.error(f"❌ Failed to read Statcast CSV parts: {e}")
        st.stop()

    # Validate required columns
    required_cols = ["plate_x", "plate_z"]
    missing = [c for c in required_cols if c not in statcast_df.columns]
    if missing:
        st.error(f"❌ Missing required column(s): {', '.join(missing)}")
        st.stop()

    # Use existing processor logic
    from data_processor import LineupProtectionProcessor
    processor = LineupProtectionProcessor(".")
    processor.statcast = statcast_df
    processor.load_all_data()

    df = processor.build_full_dataset()
    return df, processor

def calculate_adjusted_woba(df: pd.DataFrame, layers: list) -> pd.DataFrame:
    """Calculate adjusted wOBA based on selected layers."""
    df = df.copy()

    df['adjusted_wOBA'] = df['wOBA']
    df['total_selected_adj'] = 0.0

    if 'Lineup Protection' in layers:
        df['adjusted_wOBA'] = df['adjusted_wOBA'] - df['protection_adj'].fillna(0)
        df['total_selected_adj'] += df['protection_adj'].fillna(0)

    if 'Park Factors' in layers:
        df['adjusted_wOBA'] = df['adjusted_wOBA'] - df['park_adj'].fillna(0)
        df['total_selected_adj'] += df['park_adj'].fillna(0)

    if 'Pitcher Quality' in layers:
        df['adjusted_wOBA'] = df['adjusted_wOBA'] + df['pitcher_adj'].fillna(0)
        df['total_selected_adj'] -= df['pitcher_adj'].fillna(0)

    if 'Pitch Location' in layers:
        df['adjusted_wOBA'] = df['adjusted_wOBA'] - df['pitch_quality_adj'].fillna(0)
        df['total_selected_adj'] += df['pitch_quality_adj'].fillna(0)

    df['wOBA_diff'] = df['adjusted_wOBA'] - df['wOBA']
    return df

def main():
    st.title("⚾ Lineup Protection Projection Tool")
    st.markdown("*Isolating true hitter talent by controlling for context factors*")

    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Select View",
        ["🏠 Overview", "👤 Player Analysis", "📊 Leaderboards", "🔬 Methodology", "📈 Visualizations"]
    )

    st.sidebar.divider()
    st.sidebar.subheader("🎚️ Adjustment Layers")
    st.sidebar.caption("Toggle layers to isolate effects:")

    layers = []
    if st.sidebar.checkbox("Lineup Protection", value=True, help="Adjust for on-deck hitter quality"):
        layers.append("Lineup Protection")
    if st.sidebar.checkbox("Park Factors", value=True, help="Adjust for ballpark effects"):
        layers.append("Park Factors")
    if st.sidebar.checkbox("Pitcher Quality", value=True, help="Adjust for opposing pitcher quality"):
        layers.append("Pitcher Quality")
    if st.sidebar.checkbox("Pitch Location", value=True, help="Adjust for pitch location quality"):
        layers.append("Pitch Location")

    st.sidebar.caption(f"**{len(layers)} layer(s) active**")

    with st.spinner("Loading data..."):
        try:
            df, processor = load_data()
            df = calculate_adjusted_woba(df, layers)
            st.sidebar.success(f"✅ {len(df)} players loaded")
        except Exception as e:
            st.error(f"Error loading data: {e}")
            return

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


def show_overview(df: pd.DataFrame, layers: list):
    st.header("Project Overview")

    if layers:
        st.info(f"**Active Adjustments:** {', '.join(layers)}")
    else:
        st.warning("**No adjustments selected** - showing raw observed stats")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("""
        ### The Problem
        Traditional batting metrics capture what happened, but not **why**:

        - **Lineup Protection**: Hitters with elite batters behind them see better pitches
        - **Park Effects**: Coors Field inflates; T-Mobile Park suppresses
        - **Pitcher Quality**: Schedule affects matchups
        - **Pitch Location**: Better protection = more hittable pitches

        ### The Solution
        Toggle layers in the sidebar to isolate each effect individually.
        """)

    with col2:
        st.metric("Players", len(df))
        st.metric("Pitches Analyzed", "713,703")
        st.metric("Season", "2024")

    st.divider()

    col1, col2, col3 = st.columns(3)

    with col1:
        top = df.loc[df['total_selected_adj'].idxmax()]
        st.markdown("**Most Boosted**")
        st.markdown(f"### {top['Name']}")
        st.caption(f"{top['Team']} | +{top['total_selected_adj']:.3f} wOBA")

    with col2:
        bottom = df.loc[df['total_selected_adj'].idxmin()]
        st.markdown("**Most Suppressed**")
        st.markdown(f"### {bottom['Name']}")
        st.caption(f"{bottom['Team']} | {bottom['total_selected_adj']:.3f} wOBA")

    with col3:
        if layers:
            r = df[['wOBA', 'adjusted_wOBA']].corr().iloc[0, 1]
            st.markdown("**Correlation**")
            st.markdown(f"### r = {r:.3f}")
            st.caption("Observed vs Adjusted")


def show_player_analysis(df: pd.DataFrame, layers: list):
    st.header("👤 Player Analysis")

    if layers:
        st.info(f"**Active:** {', '.join(layers)}")

    player_names = sorted(df['Name'].dropna().unique())
    default_idx = player_names.index('Aaron Judge') if 'Aaron Judge' in player_names else 0
    selected = st.selectbox("Select Player", player_names, index=default_idx)

    player = df[df['Name'] == selected].iloc[0]

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader(player['Name'])
        st.caption(f"{player['Team']} | {int(player['PA'])} PA")

        st.markdown("#### Observed")
        st.metric("wOBA", f"{player['wOBA']:.3f}")
        st.metric("wRC+", f"{player['wRC+']:.0f}" if pd.notna(player.get('wRC+')) else "N/A")

        st.markdown("#### Adjusted")
        if layers:
            diff = player['adjusted_wOBA'] - player['wOBA']
            st.metric("wOBA", f"{player['adjusted_wOBA']:.3f}", delta=f"{diff:+.3f}", delta_color="inverse")
        else:
            st.caption("Select layers to see adjustments")

    with col2:
        st.markdown("#### Layer-by-Layer Breakdown")

        layer_info = [
            ("🛡️ Lineup Protection", player.get('protection_adj', 0), player.get('avg_protection_score'),
             'Lineup Protection' in layers, "On-deck hitter wOBA"),
            ("🏟️ Park Factors", player.get('park_adj', 0), player.get('park_factor'),
             'Park Factors' in layers, "Park factor (100=neutral)"),
            ("⚾ Pitcher Quality", -player.get('pitcher_adj', 0), player.get('avg_pitcher_fip_minus'),
             'Pitcher Quality' in layers, "Avg opp FIP- (100=avg)"),
            ("🎯 Pitch Location", player.get('pitch_quality_adj', 0), player.get('heart_pct'),
             'Pitch Location' in layers, "Heart% of pitches")
        ]

        for name, adj, raw, active, desc in layer_info:
            col_a, col_b, col_c = st.columns([2, 1, 1])
            with col_a:
                status = "✅" if active else "⬜"
                st.markdown(f"{status} **{name}**")
            with col_b:
                if raw is not None and pd.notna(raw):
                    if 'Heart' in desc:
                        st.caption(f"{raw*100:.1f}%")
                    elif 'Park' in desc or 'FIP' in desc:
                        st.caption(f"{raw:.0f}")
                    else:
                        st.caption(f"{raw:.3f}")
                else:
                    st.caption("N/A")
            with col_c:
                if adj is not None and pd.notna(adj):
                    color = "🟢" if adj < 0 else "🔴" if adj > 0 else "⚪"
                    st.caption(f"{color} {-adj:+.3f}")
                else:
                    st.caption("N/A")

        st.divider()

        # Waterfall chart
        waterfall_x = ['Observed']
        waterfall_y = [player['wOBA']]
        waterfall_measure = ['absolute']

        if 'Lineup Protection' in layers:
            waterfall_x.append('Protection')
            waterfall_y.append(-player.get('protection_adj', 0))
            waterfall_measure.append('relative')
        if 'Park Factors' in layers:
            waterfall_x.append('Park')
            waterfall_y.append(-player.get('park_adj', 0))
            waterfall_measure.append('relative')
        if 'Pitcher Quality' in layers:
            waterfall_x.append('Pitchers')
            waterfall_y.append(player.get('pitcher_adj', 0))
            waterfall_measure.append('relative')
        if 'Pitch Location' in layers:
            waterfall_x.append('Location')
            waterfall_y.append(-player.get('pitch_quality_adj', 0))
            waterfall_measure.append('relative')

        waterfall_x.append('Adjusted')
        waterfall_y.append(0)
        waterfall_measure.append('total')

        fig = go.Figure(go.Waterfall(
            x=waterfall_x, y=waterfall_y, measure=waterfall_measure,
            connector={"line": {"color": "gray"}},
            increasing={"marker": {"color": "#28a745"}},
            decreasing={"marker": {"color": "#dc3545"}},
            totals={"marker": {"color": "#007bff"}}
        ))
        fig.update_layout(title="wOBA Adjustment Waterfall", height=350, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)


def show_leaderboards(df: pd.DataFrame, layers: list):
    st.header("📊 Leaderboards")

    active_str = ', '.join(layers) if layers else "None"
    st.info(f"**Active Layers:** {active_str}")

    lb_options = ["Adjusted wOBA", "Biggest Risers", "Biggest Fallers"]
    lb_options.extend(["Protection Effect Only", "Park Effect Only"])

    lb_type = st.radio("Leaderboard", lb_options, horizontal=True)
    min_pa = st.slider("Min PA", 100, 500, 300)
    filtered = df[df['PA'] >= min_pa].copy()

    if lb_type == "Adjusted wOBA":
        show_df = filtered.nlargest(25, 'adjusted_wOBA')[
            ['Name', 'Team', 'PA', 'wOBA', 'adjusted_wOBA', 'total_selected_adj']
        ].copy()
        show_df.columns = ['Player', 'Team', 'PA', 'Observed', 'Adjusted', 'Total Adj']

    elif lb_type == "Biggest Risers":
        show_df = filtered.nlargest(25, 'wOBA_diff')[
            ['Name', 'Team', 'PA', 'wOBA', 'adjusted_wOBA', 'wOBA_diff']
        ].copy()
        show_df.columns = ['Player', 'Team', 'PA', 'Observed', 'Adjusted', 'Change']

    elif lb_type == "Biggest Fallers":
        show_df = filtered.nsmallest(25, 'wOBA_diff')[
            ['Name', 'Team', 'PA', 'wOBA', 'adjusted_wOBA', 'wOBA_diff']
        ].copy()
        show_df.columns = ['Player', 'Team', 'PA', 'Observed', 'Adjusted', 'Change']

    elif lb_type == "Protection Effect Only":
        filtered['prot_adj_woba'] = filtered['wOBA'] - filtered['protection_adj'].fillna(0)
        show_df = filtered.nlargest(25, 'protection_adj')[
            ['Name', 'Team', 'PA', 'avg_protection_score', 'wOBA', 'protection_adj', 'prot_adj_woba']
        ].copy()
        show_df.columns = ['Player', 'Team', 'PA', 'Protection Score', 'Observed wOBA', 'Protection Boost', 'Prot-Adj wOBA']

        st.markdown("""
        ### How Lineup Protection Works

        **Protection Score** = Average wOBA of the on-deck hitter across all plate appearances.

        When you have an elite hitter behind you (like Aaron Judge behind Juan Soto), pitchers can't
        "pitch around" you as easily. They have to attack you, giving you better pitches.

        **Protection Boost** = How much the player's observed wOBA is inflated by this advantage.

        **Prot-Adj wOBA** = Observed wOBA minus the protection boost = performance in neutral lineup context.
        """)

    elif lb_type == "Park Effect Only":
        filtered['park_adj_woba'] = filtered['wOBA'] - filtered['park_adj'].fillna(0)
        show_df = filtered.nlargest(25, 'park_adj')[
            ['Name', 'Team', 'PA', 'park_factor', 'wOBA', 'park_adj', 'park_adj_woba']
        ].copy()
        show_df.columns = ['Player', 'Team', 'PA', 'Park Factor', 'Observed wOBA', 'Park Boost', 'Park-Adj wOBA']

        st.markdown("""
        **Park Factor** > 100 = hitter-friendly park (inflates stats)

        **Park Factor** < 100 = pitcher-friendly park (suppresses stats)
        """)

    st.dataframe(show_df.round(3), use_container_width=True, hide_index=True)


def show_methodology():
    st.header("🔬 Methodology")

    tab1, tab2, tab3 = st.tabs(["Lineup Protection (Detailed)", "Other Layers", "Data Sources"])

    with tab1:
        st.markdown("""
        ## Lineup Protection: The Core Innovation

        ### The Theory

        When a dangerous hitter bats behind you, pitchers face a dilemma:

        | Option | Risk |
        |--------|------|
        | Pitch around you | Walk you, still face the dangerous hitter |
        | Attack you | Give you hittable pitches |

        **Result**: Protected hitters see better pitches → inflated stats.

        ---

        ### Step-by-Step Calculation

        #### Step 1: Identify On-Deck Hitter for Every PA

        Using Statcast data, for each of 79,300 qualified plate appearances, we identify
        who was due up next:

        ```
        Game 1, Inning 1:
          PA #1: Soto batting → Judge on deck
          PA #2: Judge batting → Stanton on deck
          PA #3: Stanton batting → Rizzo on deck
        ...
        ```

        #### Step 2: Look Up On-Deck Hitter's Season wOBA

        For each PA, we assign the on-deck hitter's 2024 season wOBA as the "protection"
        for that plate appearance.

        ```python
        # Example for one Soto PA
        on_deck_hitter = "Aaron Judge"
        protection_value = judge_season_woba  # .476
        ```

        #### Step 3: Average Protection Across All PA

        ```python
        soto_protection_score = mean([
            judge_woba,    # PA #1: Judge on deck
            judge_woba,    # PA #2: Judge on deck
            stanton_woba,  # PA #3: Stanton on deck (Judge DHing)
            ...
        ])
        # Result: Soto avg protection = .471
        ```

        #### Step 4: Compare to League Average

        ```python
        league_avg_protection = 0.331  # League average wOBA

        soto_protection_diff = 0.471 - 0.331 = +0.140
        judge_protection_diff = 0.298 - 0.331 = -0.033
        ```

        #### Step 5: Convert to wOBA Adjustment

        Based on research, we estimate that +0.100 in protection score difference
        translates to approximately +0.015 wOBA boost:

        ```python
        coefficient = 0.15  # wOBA points per protection score point

        soto_protection_boost = 0.140 × 0.15 = +0.021 wOBA
        judge_protection_penalty = -0.033 × 0.15 = -0.005 wOBA
        ```

        ---

        ### Real Examples

        #### Juan Soto (Best Protected)
        | Metric | Value |
        |--------|-------|
        | Protection Score | .471 (Aaron Judge behind him) |
        | League Average | .331 |
        | Protection Diff | +.140 |
        | **wOBA Boost** | **+.021** |
        | Observed wOBA | .421 |
        | Protection-Adjusted wOBA | .400 |

        **Interpretation**: About .021 of Soto's .421 wOBA comes from lineup protection advantage.

        #### Aaron Judge (Poorly Protected)
        | Metric | Value |
        |--------|-------|
        | Protection Score | .298 (inconsistent hitters behind) |
        | League Average | .331 |
        | Protection Diff | -.033 |
        | **wOBA Penalty** | **-.005** |
        | Observed wOBA | .476 |
        | Protection-Adjusted wOBA | .481 |

        **Interpretation**: Judge produces elite numbers *despite* lack of protection.
        His true talent may be even higher than observed.

        ---

        ### Key Insights

        1. **Protected hitters may be overvalued** - their stats include a pitch quality boost
        2. **Unprotected hitters may be undervalued** - they face tougher pitches
        3. **This is testable** - players changing teams/lineup spots should show predictable changes
        """)

    with tab2:
        st.markdown("""
        ## Other Adjustment Layers

        ### Park Factors

        ```python
        park_factor = team_5yr_park_factor / 100
        park_adjusted_wOBA = observed_wOBA × (1 / park_factor)
        ```

        Example: Rockies hitter with .315 wOBA at Coors (113 PF):
        - Park-adjusted: .315 × (100/113) = .279

        ### Pitcher Quality Faced

        ```python
        avg_opp_fip_minus = mean(opponent_pitcher_FIP_minus for all PA)
        pitcher_adj = (100 - avg_opp_fip_minus) × 0.001
        ```

        Facing 90 FIP- pitchers (elite) vs 100 (average) = +.010 adjustment.

        ### Pitch Location Quality

        ```python
        heart_pct = pitches_in_heart_zone / total_pitches
        pitch_adj = (heart_pct - league_avg_heart_pct) × 0.15
        ```

        Captures the *mechanism* of protection - more hittable pitch locations.
        """)

    with tab3:
        st.markdown("""
        ## Data Sources

        | Source | Data | Records |
        |--------|------|---------|
        | Baseball Savant | Pitch-by-pitch Statcast | 713,703 pitches |
        | FanGraphs | Batting stats (qualified) | 129 batters |
        | FanGraphs | Pitching stats (qualified) | 58 pitchers |
        | FanGraphs | 5-year park factors | 30 teams |
        | FanGraphs | wOBA linear weights | 2024 season |

        ### Key Fields Used

        **From Statcast:**
        - `batter`, `pitcher` - player IDs
        - `game_pk`, `at_bat_number`, `inning` - for sequencing
        - `plate_x`, `plate_z` - pitch location
        - `on_1b`, `on_2b`, `on_3b` - base state

        **From FanGraphs:**
        - `wOBA`, `wRC+` - performance metrics
        - `FIP`, `xFIP` - pitcher quality
        - Park factors by team
        
        ### Data Storage
        
        The Statcast data file (~400MB) is hosted on Google Drive and will be 
        downloaded automatically on first run.
        """)


def show_visualizations(df: pd.DataFrame, layers: list):
    st.header("📈 Visualizations")

    viz = st.selectbox("Select", [
        "Observed vs Adjusted Scatter",
        "Protection Score vs wOBA",
        "Layer Impact Magnitudes",
        "Team Context Effects"
    ])

    if viz == "Observed vs Adjusted Scatter":
        fig = px.scatter(
            df, x='wOBA', y='adjusted_wOBA',
            hover_name='Name', hover_data=['Team', 'total_selected_adj'],
            color='total_selected_adj', color_continuous_scale='RdYlGn_r',
            title=f'Observed vs Adjusted ({", ".join(layers) if layers else "No layers"})'
        )
        fig.add_trace(go.Scatter(x=[.25,.48], y=[.25,.48], mode='lines',
                                  line=dict(dash='dash', color='gray'), showlegend=False))
        fig.update_layout(height=600)
        st.plotly_chart(fig, use_container_width=True)

    elif viz == "Protection Score vs wOBA":
        fig = px.scatter(
            df, x='avg_protection_score', y='wOBA',
            hover_name='Name', trendline='ols',
            title='Does Protection Correlate with Performance?'
        )
        fig.update_layout(height=600, xaxis_title='Protection Score', yaxis_title='Observed wOBA')
        st.plotly_chart(fig, use_container_width=True)

    elif viz == "Layer Impact Magnitudes":
        impacts = pd.DataFrame({
            'Layer': ['Protection', 'Park', 'Pitcher', 'Location'],
            'Avg |Adj|': [
                df['protection_adj'].abs().mean(),
                df['park_adj'].abs().mean(),
                df['pitcher_adj'].abs().mean(),
                df['pitch_quality_adj'].abs().mean()
            ]
        })
        fig = px.bar(impacts, x='Layer', y='Avg |Adj|', title='Average Absolute Adjustment by Layer')
        st.plotly_chart(fig, use_container_width=True)

    elif viz == "Team Context Effects":
        team = df.groupby('Team').agg({
            'protection_adj': 'mean', 'park_adj': 'mean', 'wOBA': 'mean'
        }).reset_index()
        fig = px.scatter(team, x='protection_adj', y='park_adj', size='wOBA',
                         hover_name='Team', title='Team-Level Context')
        st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
