import streamlit as st
import pandas as pd
import numpy as np
import io
import matplotlib.pyplot as plt
from datetime import datetime

# --------------------------------------------
# Generate Dummy Data
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
st.title("📈 Trend Analysis: MOB vs DPD%, DPD Thresholds & Cohort Heatmaps")

st.write("""
This app allows you to analyze **loan performance over time**
using:
- **Months on Book (MOB)**
- **DPD thresholds (1+, 10+, 30+, 60+, 90+)**
- **Cohort trends**
- **Cohort heatmaps**

You can upload your own dataset or use dummy data.
""")

# ---------------- 1. Dataset selection ----------------
st.subheader("📌 Select Dataset")

use_dummy = st.radio("Use dummy dataset?", ["Yes", "No (upload CSV)"])

if use_dummy == "Yes":
    st.info("Loading default dummy dataset (economic stress simulation)…")

    try:
        df = pd.read_csv("economic_dpd_dataset.csv", parse_dates=["origination_date"])
        st.success("Economic dummy dataset loaded.")
        st.dataframe(df.head())

    except FileNotFoundError:
        st.error("""
        ❌ Could not find **economic_dpd_dataset.csv**.

        Please place the file in the same directory as this Streamlit script.
        """)
        st.stop()

else:
    file = st.file_uploader("Upload CSV with 'origination_date' & 'days_past_due'", type="csv")
    if file is None:
        st.stop()

    df = pd.read_csv(file, parse_dates=["origination_date"])
    st.success("File uploaded.")
    st.dataframe(df.head())


# ---------------- 2. Minimum origination date ----------------
st.subheader("📅 Minimum Origination Date Filter")

min_date = st.date_input("Select minimum origination date:", df["origination_date"].min().date())
df = df[df["origination_date"] >= pd.to_datetime(min_date)]


# ---------------- 3. Run date + MOB ----------------
run_date = st.date_input("Select Run Date:", datetime.today())
df["run_date"] = pd.to_datetime(run_date)

df["days_diff"] = (df["run_date"] - df["origination_date"]).dt.days
df["months_on_book"] = (df["days_diff"] / 30.44).clip(lower=0).astype(int)

df["origination_year"] = df["origination_date"].dt.year
df["origination_quarter"] = df["origination_date"].dt.quarter


# ---------------- 4. DPD threshold selection ----------------
st.subheader("⚙️ DPD Threshold Selection")

dpd_threshold = st.number_input(
    "Enter DPD Threshold (Example: 1 for 1+, 30 for 30+):", 
    min_value=1, 
    max_value=120, 
    value=1
)

df["dpd_flag"] = df["days_past_due"] >= dpd_threshold


# ---------------- 5. Group selection ----------------
st.subheader("📊 Grouping Options")

group_choice = st.selectbox(
    "Choose grouping:",
    ["By Year", "By Year & Quarter", "By Quarter Only (Seasonality)"]
)

if group_choice == "By Year":
    groups = df.groupby("origination_year")
    cohort_label = "origination_year"

elif group_choice == "By Year & Quarter":
    df["year_quarter"] = df["origination_year"].astype(str) + " Q" + df["origination_quarter"].astype(str)
    groups = df.groupby("year_quarter")
    cohort_label = "year_quarter"

else:
    groups = df.groupby("origination_quarter")
    cohort_label = "origination_quarter"


# ---------------- 6. Line Plot - DPD% trend ----------------
st.subheader("📈 DPD% Trend Across Cohorts")

fig, ax = plt.subplots(figsize=(9, 6))

for name, data in groups:
    mob_group = (
        data.groupby("months_on_book")["dpd_flag"]
        .mean()
        .sort_index()
        .reset_index()
    )

    mob_group["dpd_percent"] = mob_group["dpd_flag"] * 100

    ax.plot(
        mob_group["months_on_book"], 
        mob_group["dpd_percent"], 
        label=str(name)
    )

ax.set_xlabel("Months on Book (MOB)")
ax.set_ylabel(f"DPD% (DPD ≥ {dpd_threshold})")
ax.set_title(f"DPD% Trend Across Cohorts (Threshold: {dpd_threshold}+ DPD)")
ax.legend(title="Cohort")
ax.grid(True)

st.pyplot(fig)

st.write(f"""
### 📝 Interpretation:  
This plot shows the **percentage of accounts in each cohort** that have  
**DPD ≥ {dpd_threshold}** at each MOB.

- If curves rise sharply → early delinquency buildup (high credit risk)  
- Flat or declining curves → stable cohorts  
- Comparing cohorts tells you **vintage quality**  
""")


# ---------------- 7. Cohort Heatmap ----------------
st.subheader("🔥 Cohort Heatmap (MOB × Cohort)")

# Pivot table: rows = cohort, columns = MOB
heatmap_data = (
    df.groupby([cohort_label, "months_on_book"])["dpd_flag"]
    .mean()
    .unstack(fill_value=0) * 100
)

fig2, ax2 = plt.subplots(figsize=(10, 6))
im = ax2.imshow(heatmap_data, aspect='auto')

ax2.set_xticks(np.arange(len(heatmap_data.columns)))
ax2.set_xticklabels(heatmap_data.columns)

ax2.set_yticks(np.arange(len(heatmap_data.index)))
ax2.set_yticklabels(heatmap_data.index)

plt.colorbar(im, label=f"DPD% (DPD ≥ {dpd_threshold})")
ax2.set_title(f"Cohort Heatmap: DPD% (Threshold: {dpd_threshold}+)")
ax2.set_xlabel("Months on Book (MOB)")
ax2.set_ylabel("Cohort")

st.pyplot(fig2)

st.write(f"""
### 📝 Interpretation:  
This heatmap gives a **vintage-quality view**:

- **Rows = Cohorts** (year or quarter)  
- **Columns = MOB**  
- **Colors = DPD%** for DPD ≥ {dpd_threshold}

📌 **Use Case:**  
- Quickly detect weak cohorts (darker colors early)  
- Compare performance at same MOB  
- Identify underwriting or economic changes  
""")


# ---------------- 8. Download options ----------------
png_buf = download_plot(fig)
heat_buf = download_plot(fig2)

st.download_button("⬇️ Download DPD% Trend Plot", png_buf, "dpd_trend.png")
st.download_button("⬇️ Download Cohort Heatmap", heat_buf, "cohort_heatmap.png")
