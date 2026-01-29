import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import traceback

st.set_page_config(page_title="Debug: Lineup-Adjusted wOBA", layout="wide")

st.title("🧪 Debug: Lineup-Adjusted wOBA Leaderboard")

# ========== TRY TO LOAD DATA + RUN VISUALS ==========
try:
    st.info("Loading and building full dataset...")

    # Import your full pipeline function
    from data_processor import build_full_dataset  # adjust this path if needed
    df = build_full_dataset()

    st.success("✅ Full dataset loaded successfully!")
    st.write(f"{len(df)} players, {df.shape[1]} columns")
    st.dataframe(df.head())

    # ========= Visualizations =========
    st.header("📈 Visualizations")
    layers = ['Protection', 'Park', 'Pitcher', 'Location']

    viz = st.selectbox("Select plot", [
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
            title=f'Observed vs Adjusted ({", ".join(layers)})'
        )
        fig.add_trace(go.Scatter(x=[.25, .48], y=[.25, .48], mode='lines',
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
            'protection_adj': 'mean',
            'park_adj': 'mean',
            'wOBA': 'mean'
        }).reset_index()
        fig = px.scatter(team, x='protection_adj', y='park_adj', size='wOBA',
                         hover_name='Team', title='Team-Level Context')
        st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error("🚨 An error occurred while running the app:")
    st.code(traceback.format_exc())
