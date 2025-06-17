import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os

def analyze_excel(excel_path):
    # Load the Excel file without assuming a header
    df_full = pd.read_excel(excel_path, header=None)

    # Extract relevant data
    df_data = df_full.iloc[2:, [3, 4, 5]]
    df_data.columns = ["PRE", "POST", "INCREMENT"]
    df_data = df_data.dropna()

    # Convert strings with commas to floats
    df_data["PRE"] = df_data["PRE"].astype(str).str.replace(",", ".").astype(float)
    df_data["POST"] = df_data["POST"].astype(str).str.replace(",", ".").astype(float)
    df_data["INCREMENT"] = df_data["INCREMENT"].astype(str).str.replace(",", ".").astype(float)

    n = len(df_data)

    # ---- PRE vs POST Boxplot ----
    df_melted = df_data[["PRE", "POST"]].melt(var_name="Phase", value_name="Volume (cm³)")
    plt.figure(figsize=(7, 5))
    sns.boxplot(x="Phase", y="Volume (cm³)", data=df_melted)

    for phase in ["PRE", "POST"]:
        values = df_data[phase]
        q1, q3 = np.percentile(values, [25, 75])
        iqr = q3 - q1
        lower_whisker = max(values[values >= (q1 - 1.5 * iqr)].min(), values.min())
        upper_whisker = min(values[values <= (q3 + 1.5 * iqr)].max(), values.max())
        med = np.median(values)

        xpos = ["PRE", "POST"].index(phase)
        plt.text(xpos, q3 + 0.5, f"↑ Q3: {q3:.2f}", ha='center', fontsize=9)
        plt.text(xpos, q1 - 0.5, f"↓ Q1: {q1:.2f}", ha='center', fontsize=9)
        plt.text(xpos, med, f"● Med: {med:.2f}", ha='center', fontsize=9, color='darkred')
        plt.text(xpos, lower_whisker - 0.5, f"Min*: {lower_whisker:.2f}", ha='center', fontsize=8, color='gray')
        plt.text(xpos, upper_whisker + 0.5, f"Max*: {upper_whisker:.2f}", ha='center', fontsize=8, color='gray')

    plt.title(f"Spinal Cord Volume — PRE vs POST (n = {n})")
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    # ---- INCREMENT Boxplot ----
    plt.figure(figsize=(6, 5))
    sns.boxplot(y=df_data["INCREMENT"])
    q1, q3 = np.percentile(df_data["INCREMENT"], [25, 75])
    iqr = q3 - q1
    lower_whisker = max(df_data["INCREMENT"][df_data["INCREMENT"] >= (q1 - 1.5 * iqr)].min(), df_data["INCREMENT"].min())
    upper_whisker = min(df_data["INCREMENT"][df_data["INCREMENT"] <= (q3 + 1.5 * iqr)].max(), df_data["INCREMENT"].max())
    med = np.median(df_data["INCREMENT"])

    plt.text(0, q3 + 1, f"↑ Q3: {q3:.2f}%", ha='center', fontsize=9)
    plt.text(0, q1 - 1, f"↓ Q1: {q1:.2f}%", ha='center', fontsize=9)
    plt.text(0, med, f"● Med: {med:.2f}%", ha='center', fontsize=9, color='darkred')
    plt.text(0, lower_whisker - 1.5, f"Min*: {lower_whisker:.2f}%", ha='center', fontsize=8, color='gray')
    plt.text(0, upper_whisker + 1.5, f"Max*: {upper_whisker:.2f}%", ha='center', fontsize=8, color='gray')

    plt.title(f"Increment [%] — POST vs PRE (n = {n})")
    plt.ylabel("Increment (%)")
    plt.grid(True)
    plt.tight_layout()
    plt.show()

def main():
    print("🔬 Individual Volume Analysis Tool")
    
    excel_path = input("Enter the path to the Excel file with volume data: ").strip().strip('"')
    if not os.path.exists(excel_path):
        print(f"❌ Excel file not found: {excel_path}")
        return

    print("📊 Analyzing Excel...")
    analyze_excel(excel_path)
    print("✅ Analysis complete. Visualizations displayed.")

if __name__ == "__main__":
    main()
