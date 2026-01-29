"""
DEBUG — Lineup Protection Projection Tool
Purpose: identify exactly where Streamlit Cloud is failing
"""

import streamlit as st
import traceback
import pandas as pd
import glob
import sys
import os

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="DEBUG — Lineup Protection Tool",
    page_icon="⚾",
    layout="wide"
)

st.title("🛠️ DEBUG: Lineup-Adjusted wOBA App")
st.caption("This app prints every step so failures cannot hide.")

# =========================
# ENVIRONMENT CHECKS
# =========================
st.subheader("Step 0: Environment")

st.write("Python version:", sys.version)
st.write("Working directory:", os.getcwd())
st.write("Files in repo root:")
st.code("\n".join(sorted(os.listdir("."))))

# =========================
# STEP 1: IMPORT CHECK
# =========================
st.subheader("Step 1: Import data_processor")

try:
    from data_processor import LineupProtectionProcessor
    st.success("✅ Imported LineupProtectionProcessor")
except Exception:
    st.error("❌ Failed importing LineupProtectionProcessor")
    st.code(traceback.format_exc())
    st.stop()

# =========================
# STEP 2: FIND CSV CHUNKS
# =========================
st.subheader("Step 2: Locate Statcast CSV chunks")

csv_parts = sorted(glob.glob("statcast_2024_part*.csv"))
st.write("Found CSV files:", csv_parts)

if not csv_parts:
    st.error("❌ No statcast CSV chunks found")
    st.stop()

# =========================
# STEP 3: LOAD CSVs
# =========================
st.subheader("Step 3: Load Statcast CSVs")

try:
    statcast_df = pd.concat(
        (pd.read_csv(f, low_memory=False) for f in csv_parts),
        ignore_index=True
    )
    st.success(f"✅ Loaded Statcast data: {statcast_df.shape}")
except Exception:
    st.error("❌ Failed loading Statcast CSVs")
    st.code(traceback.format_exc())
    st.stop()

st.write("Statcast columns:")
st.code(", ".join(statcast_df.columns[:40]) + " ...")

# =========================
# STEP 4: VALIDATE REQUIRED COLUMNS
# =========================
st.subheader("Step 4: Validate required Statcast columns")

required_cols = ["plate_x", "plate_z", "batter", "pitcher"]
missing = [c for c in required_cols if c not in statcast_df.columns]

if missing:
    st.error(f"❌ Missing required columns: {missing}")
    st.stop()
else:
    st.success("✅ Required Statcast columns present")

# =========================
# STEP 5: INITIALIZE PROCESSOR
# =========================
st.subheader("Step 5: Initialize LineupProtectionProcessor")

try:
    processor = LineupProtectionProcessor(".")
    st.success("✅ Processor instantiated")
except Exception:
    st.error("❌ Failed to instantiate processor")
    st.code(traceback.format_exc())
    st.stop()

# =========================
# STEP 6: ATTACH STATCAST DATA
# =========================
st.subheader("Step 6: Attach Statcast data to processor")

try:
    processor.statcast = statcast_df
    st.success("✅ Statcast data attached to processor")
except Exception:
    st.error("❌ Failed attaching statcast to processor")
    st.code(traceback.format_exc())
    st.stop()

# =========================
# STEP 7: LOAD AUX DATA
# =========================
st.subheader("Step 7: processor.load_all_data()")

try:
    processor.load_all_data()
    st.success("✅ load_all_data() completed")
except Exception:
    st.error("❌ load_all_data() failed")
    st.code(traceback.format_exc())
    st.stop()

# =========================
# STEP 8: BUILD FULL DATASET
# =========================
st.subheader("Step 8: processor.build_full_dataset()")

try:
    df = processor.build_full_dataset()
    st.success(f"✅ Full dataset built: {df.shape}")
except Exception:
    st.error("❌ build_full_dataset() failed")
    st.code(traceback.format_exc())
    st.stop()

# =========================
# STEP 9: SANITY CHECK OUTPUT
# =========================
st.subheader("Step 9: Dataset sanity checks")

expected_cols = [
    "Name", "Team", "PA", "wOBA",
    "protection_adj", "park_adj",
    "pitcher_adj", "pitch_quality_adj"
]

missing = [c for c in expected_cols if c not in df.columns]

if missing:
    st.warning(f"⚠️ Missing expected output columns: {missing}")
else:
    st.success("✅ All expected output columns present")

st.write("Preview of final dataset:")
st.dataframe(df.head(10))

# =========================
# DONE
# =========================
st.success("🎉 DEBUG APP FINISHED — NO SILENT FAILURES")
