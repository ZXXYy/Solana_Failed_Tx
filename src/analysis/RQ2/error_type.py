import json
import ast

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def get_failed_count_for_type(df_types, error_type):
    error_logs = list(df_types[error_type])
    total_count = 0
    with open(f"/data0/xiaoyez/Solana_Failed_Tx/data/failed_txs_one_year.log", "r") as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            if line.strip() not in error_logs:
                continue
            # print(line.strip())
            programs = ast.literal_eval(lines[i+1])
            for program_id, cnt in programs.items():
                total_count += cnt
    return total_count

def get_total_cnt(df_types):
    total_counts, uncategorized_cnt = 0, 0
    total_error_logs = []
    for col in df_types.columns:
        total_error_logs.extend(list(df_types[col]))
    with open(f"/data0/xiaoyez/Solana_Failed_Tx/data/failed_txs_one_year.log", "r") as f:
        lines = f.readlines()
        for i in range(0, len(lines), 3):
            line = lines[i]
            programs = ast.literal_eval(lines[i+1])
            for program_id, cnt in programs.items():
                if line.strip() not in total_error_logs:
                    uncategorized_cnt += cnt
                total_counts += cnt
    return total_counts, uncategorized_cnt

def plot_pie(type_percent):
    # sort type_percent
    unknown_value = type_percent.get('Unknown/Uncategorized', 0)  # Save unknown value if it exists
    filtered_dict = {k: v for k, v in type_percent.items() if k != 'Unknown/Uncategorized'}
    sorted_dict = dict(sorted(filtered_dict.items(), key=lambda x: x[1], reverse=True))

    # Add unknown back at the end if it existed
    if 'Unknown/Uncategorized' in type_percent:
        sorted_dict['Unknown/Uncategorized'] = unknown_value
    type_percent = sorted_dict
    
    error_types = list(type_percent.keys())
    percentages = list(type_percent.values())
    # Create figure and axis
    plt.figure(figsize=(16, 8))

    # Create pie chart
    # Only show labels for sections larger than 2%
    labels = [f'{pct:.2f}%' if pct >= 2 else '' 
            for type, pct in zip(error_types, percentages)]
    # Set global font sizes
    plt.rcParams.update({
        'font.size': 20,
        'axes.titlesize': 16,
        'axes.labelsize': 14,
        'xtick.labelsize': 12,
        'ytick.labelsize': 12,
        'legend.fontsize': 18,
        'legend.title_fontsize': 18
    })
    # Colors
    colors = [(0.12, 0.47, 0.71, 0.7),  # Blue
            (1.0, 0.5, 0.05, 0.7),    # Orange
            (0.17, 0.63, 0.17, 0.7),  # Green
            (0.84, 0.15, 0.16, 0.7),  # Red
            (0.58, 0.40, 0.74, 0.7),  # Purple
            (0.55, 0.34, 0.29, 0.7),  # Brown
            (0.89, 0.47, 0.76, 0.7),  # Pink
            (0.5, 0.5, 0.5, 0.7),     # Gray
            (0.74, 0.74, 0.13, 0.7),  # Yellow
            (0.09, 0.75, 0.81, 0.7),  # Cyan
            (0.2, 0.2, 0.2, 0.7)]     # Dark Gray (for the 11th category)

    # Create pie chart
    wedges, texts, autotexts = plt.pie(percentages, 
                                    labels=labels,
                                    colors=colors,
                                    autopct='',
                                    startangle=90,
                                    textprops={'fontsize': 20},
                                    labeldistance=1.1)

    # Create legend
    legend_labels = [f"{error_type} ({pct:.2f}%)" 
                    for error_type, pct in zip(error_types, percentages)]
    plt.legend(wedges, legend_labels,
            title="Error Types",
            loc="best",
            bbox_to_anchor=(1, 0, 0.5, 1))

    # plt.title('Distribution of Error Types for Failed Transactions', pad=20)

    # Ensure the pie chart is circular
    plt.axis('equal')

    # Adjust layout to prevent legend cutoff
    plt.tight_layout()

    plt.savefig(f'/data0/xiaoyez/Solana_Failed_Tx/data/pie_error.png', dpi=300) 
# Load the data
df_types = pd.read_csv("/data0/xiaoyez/Solana_Failed_Tx/data//error_categorization_revised.csv")
total = 0
total_perct = 0
total_counts, uncategorized_cnt = get_total_cnt(df_types)
type_percent = {}
for col in df_types.columns:
    cnt = get_failed_count_for_type(df_types, col)
    print(f"{col}: {cnt}, {cnt/total_counts}")
    print("=====================================")
    if col == "Unknown":
        col = "Unknown/Uncategorized"
    type_percent[col] = cnt/total_counts * 100
    total += cnt
    total_perct += cnt/total_counts

type_percent["Unknown/Uncategorized"] += uncategorized_cnt/total_counts * 100

print(f"Uncategorized: {uncategorized_cnt}, {uncategorized_cnt/total_counts}, {total_perct + uncategorized_cnt/total_counts}")
plot_pie(type_percent)