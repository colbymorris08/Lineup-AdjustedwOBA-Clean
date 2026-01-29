import streamlit as st
import pandas as pd
import plotly.express as px
import traceback

try:
    # Title and description
    st.title("Lineup-Adjusted wOBA Leaderboard")
    st.markdown(
        "This tool evaluates hitter performance by adjusting for lineup protection, "
        "removing bias from protection quality, to better assess individual contributions."
    )

    # Upload CSV file
    uploaded_file = st.file_uploader("Upload your Lineup-Adjusted wOBA CSV", type=["csv"])

    if uploaded_file is not None:
        # Read data
        df = pd.read_csv(uploaded_file)

        # Clean column names
        df.columns = df.columns.str.strip()

        # Sidebar filters
        st.sidebar.header("Filter Options")
        team_filter = st.sidebar.multiselect("Select team(s):", df["Team"].unique(), default=df["Team"].unique())
        min_pa = st.sidebar.slider("Minimum Plate Appearances:", min_value=0, max_value=int(df["PA"].max()), value=50)

        # Apply filters
        filtered_df = df[(df["Team"].isin(team_filter)) & (df["PA"] >= min_pa)]

        # Leaderboard Table
        st.subheader("Leaderboard Table")
        leaderboard_cols = ["Name", "Team", "PA", "wOBA", "Adj_wOBA", "Adj_wOBA_Diff"]
        st.dataframe(filtered_df[leaderboard_cols].sort_values("Adj_wOBA", ascending=False), use_container_width=True)

        # Scatter Plot
        st.subheader("wOBA vs Adjusted wOBA")
        fig = px.scatter(
            filtered_df,
            x="wOBA",
            y="Adj_wOBA",
            color="Team",
            hover_data=["Name", "PA", "Adj_wOBA_Diff"],
            title="wOBA vs Adjusted wOBA (Lineup Context Removed)",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Histogram of Differences
        st.subheader("Distribution of Adjusted wOBA Differences")
        fig2 = px.histogram(
            filtered_df,
            x="Adj_wOBA_Diff",
            nbins=30,
            title="How Much Did Adjusted wOBA Differ from Raw wOBA?",
        )
        st.plotly_chart(fig2, use_container_width=True)

        # Table of biggest risers/fallers
        st.subheader("Top Risers and Fallers (Adj_wOBA vs wOBA)")
        sorted_diff = filtered_df.sort_values("Adj_wOBA_Diff", ascending=False)
        st.markdown("### Biggest Risers")
        st.dataframe(sorted_diff.head(10)[leaderboard_cols], use_container_width=True)
        st.markdown("### Biggest Fallers")
        st.dataframe(sorted_diff.tail(10)[leaderboard_cols], use_container_width=True)

except Exception as e:
    st.error("An error occurred. See details below.")
    st.code(traceback.format_exc())
