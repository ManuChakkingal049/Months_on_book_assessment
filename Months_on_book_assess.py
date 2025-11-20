import streamlit as st
import pandas as pd
import numpy as np
import io
import base64
import matplotlib.pyplot as plt
from datetime import datetime

# --------------------------------------------
# Generate Dummy Data (no months_on_book)
# --------------------------------------------
def generate_dummy_data():
    np.random.seed(42)
    dates = pd.date_range(start="2018-01-01", end="2022-12-31", freq="W")
    df = pd.DataFrame({
        "client_id": range(1, len(dates) + 1),
        "origination_date": dates,
    })
    df["days_past_due"] = np.random.randint(0, 120, size=len(df))
    return df


# --------------------------------------------
# Download plot helper
# --------------------------------------------
def download_plot(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    return buf


# --------------------------------------------
# Streamlit App Layout
# --------------------------------------------
st.title("📈 Months on Book vs Days Past Due Analysis")

st.write("""
This app analyzes **Months on Book** (calculated from a user-provided Run Date)  
and its relationship with **Days Past Due**.
""")

# ----------------------------------------------------
# Ask user if they want dummy data
# ----------------------------------------------------
st.subheader("📌 Choose Your Dataset")

use_dummy = st.radio(
    "Do you want to use the built-in dummy dataset?",
    ("Yes, use dummy data", "No, upload my own file")
)

if use_dummy == "Yes, use dummy data":
    df = generate_dummy_data()
    st.success("Using dummy data")
    st.dataframe(df.head())

else:
    uploaded = st.file_uploader("Upload your CSV file (must contain 'origination_date' column)", type=["csv"])
    if uploaded is not None:
        df = pd.read_csv(uploaded, parse_dates=["origination_date"])
        st.success("File uploaded successfully")
        st.dataframe(df.head())
    else:
        st.warning("Waiting for file upload...")
        st.stop()

# ----------------------------------------------------
# Run Date Input
# ----------------------------------------------------
st.subheader("📅 Run Date")

run_date = st.date_input(
    "Select Run Date:",
    value=datetime.today()
)

# ----------------------------------------------------
# Compute Months on Book
# ----------------------------------------------------
df["run_date"] = pd.to_datetime(run_date)
df["days_diff"] = (df["run_date"] - df["origination_date"]).dt.days
df["months_on_book"] = df["days_diff"] / 30.44  # ~avg days per month
df["months_on_book"] = df["months_on_book"].clip(lower=0)

# Add year/quarter for filtering
df["origination_year"] = df["origination_date"].dt.year
df["origination_quarter"] = df["origination_date"].dt.quarter

# ----------------------------------------------------
# User Input for Grouping
# ----------------------------------------------------
st.subheader("📊 Grouping Options")

group_choice = st.selectbox(
    "How do you want to group clients?",
    ["By Year", "By Year & Quarter", "By Quarter Only (Seasonality)"]
)

if group_choice == "By Year":
    selected_year = st.selectbox("Select Origination Year", sorted(df["origination_year"].unique()))
    filtered_df = df[df["origination_year"] == selected_year]

elif group_choice == "By Year & Quarter":
    selected_year = st.selectbox("Select Origination Year", sorted(df["origination_year"].unique()))
    available_quarters = sorted(df[df["origination_year"] == selected_year]["origination_quarter"].unique())
    selected_quarter = st.selectbox("Select Quarter", available_quarters)
    filtered_df = df[(df["origination_year"] == selected_year) &
                     (df["origination_quarter"] == selected_quarter)]

else:  # Seasonality only
    selected_quarter = st.selectbox("Select Quarter (1–4)", [1, 2, 3, 4])
    filtered_df = df[df["origination_quarter"] == selected_quarter]

# ----------------------------------------------------
# Plot Section
# ----------------------------------------------------
st.subheader("📈 Plot: Months on Book vs Days Past Due")

if filtered_df.empty:
    st.error("No data available for the selected group.")
else:
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(filtered_df["months_on_book"], filtered_df["days_past_due"])
    ax.set_xlabel("Months on Book")
    ax.set_ylabel("Days Past Due")
    ax.set_title("Months on Book vs Days Past Due")

    st.pyplot(fig)

    # Download button
    png_buf = download_plot(fig)
    st.download_button(
        label="⬇️ Download Plot as PNG",
        data=png_buf,
        file_name="mob_vs_dpd_plot.png",
        mime="image/png"
    )
