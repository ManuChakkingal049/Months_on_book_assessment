
import streamlit as st
import pandas as pd
import numpy as np
import io
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
# Streamlit App
# --------------------------------------------
st.title("📈 Trend Analysis: Months on Book vs Days Past Due")

st.write("""
This app assesses whether **cumulative Days Past Due (DPD)**  
shows a trend as clients progress through **Months on Book (MOB)**.
""")


# 1. Select Dataset
st.subheader("📌 Select Dataset")

use_dummy = st.radio("Use dummy dataset?", ["Yes", "No (upload CSV)"])

if use_dummy == "Yes":
    df = generate_dummy_data()
    st.success("Dummy data loaded.")
    st.dataframe(df.head())

else:
    file = st.file_uploader("Upload CSV with 'origination_date' and 'days_past_due'", type="csv")
    if file is None:
        st.stop()

    df = pd.read_csv(file, parse_dates=["origination_date"])
    st.success("File uploaded.")
    st.dataframe(df.head())


# 2. Run Date
st.subheader("📅 Run Date")

run_date = st.date_input("Select Run Date:", datetime.today())
df["run_date"] = pd.to_datetime(run_date)


# 3. Calculate MOB
df["days_diff"] = (df["run_date"] - df["origination_date"]).dt.days
df["months_on_book"] = (df["days_diff"] / 30.44).clip(lower=0).astype(int)

df["origination_year"] = df["origination_date"].dt.year
df["origination_quarter"] = df["origination_date"].dt.quarter


# --------------------------------------------------------
# 4. Grouping Options
# --------------------------------------------------------
st.subheader("📊 Grouping Options")

group_choice = st.selectbox(
    "Choose grouping:",
    ["By Year", "By Year & Quarter", "By Quarter Only (Seasonality)"]
)

if group_choice == "By Year":
    groups = df.groupby("origination_year")

elif group_choice == "By Year & Quarter":
    df["year_quarter"] = df["origination_year"].astype(str) + " Q" + df["origination_quarter"].astype(str)
    groups = df.groupby("year_quarter")

else:  # Seasonality only (all years combined)
    groups = df.groupby("origination_quarter")


# --------------------------------------------------------
# 5. Build Line Plot (Cumulative Trend)
# --------------------------------------------------------
st.subheader("📈 Cumulative DPD Trend Plot")

fig, ax = plt.subplots(figsize=(9, 6))

for group_name, group_data in groups:

    # Aggregate mean DPD per MOB
    temp = (
        group_data.groupby("months_on_book")["days_past_due"]
        .mean()
        .sort_index()
        .reset_index()
    )

    # Add cumulative average DPD
    temp["cumulative_dpd"] = temp["days_past_due"].expanding().mean()

    # Plot
    ax.plot(temp["months_on_book"], temp["cumulative_dpd"], label=str(group_name))

ax.set_xlabel("Months on Book (MOB)")
ax.set_ylabel("Cumulative Avg Days Past Due")
ax.set_title("Cumulative DPD Trend Across Origination Cohorts")
ax.legend(title="Cohort")
ax.grid(True)

st.pyplot(fig)


# --------------------------------------------------------
# 6. Download Plot
# --------------------------------------------------------
png_buf = download_plot(fig)
st.download_button(
    "⬇️ Download Plot as PNG",
    data=png_buf,
    file_name="cumulative_dpd_trend.png",
    mime="image/png"
)
