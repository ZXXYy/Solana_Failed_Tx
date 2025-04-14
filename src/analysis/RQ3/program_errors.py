import ast
import pymongo

import pandas as pd
import plotly.graph_objects as go

from collections import defaultdict

top_failed_programs = {
    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8": "RaydiumV4",
    "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4" : "JupiterV6", 
    "6Q4Xu2sXxMLMhS2pSBJwhDrL5AMWGbrBT3yaN48kYX7G": "6Q4Xu2sXxM",
    "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL": "ATA",
    "GDDMwNyyx8uB6zrqwBFHjLLG3TBYk2F8Az4yrQC5RzMp": "Seq Enforcer",
    "JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB": "JupiterV4",
    "9uW2TqLyfYyrcNVrgCy4jPpqDKQoBZhXWypzzFxbixQE": "9uW2TqLyfY",
    "8BR3zs8zSXetpnDjCtHWnkpSkNSydWb3PTTDuVKku2uu": "8BR3zs8zSX",
    "3J3HFc8jXxdvZQ73PeUPJmPdM2EKpKonzBaYACCXzqkv": "3J3HFc8jXx",
    "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc": "Orca",
}

def get_top_failed_program_error_logs():
    with open(f"/data0/xiaoyez/Solana_Ecosystem/src/analyze/RQ2/output_fig/failed_txs.log", "r") as f:
        lines = f.readlines()
        program_to_error_logs = defaultdict(list)
        i = 0
        while i < len(lines):
            line = lines[i]
            error_logs = line.strip()
            try:
                programs = ast.literal_eval(lines[i+1])
                percetage = lines[i+2].strip().split(" ")[0]
                percetage = float(percetage)
            except:
                assert False, f"Line {i}: Cannot convert"   
            # print(f"Error: {error_logs}")
            # print(f"Programs: {programs}")
            # print()
            for program_id, cnt in programs.items():
                if program_id in top_failed_programs.keys():
                    # print(f"Program: {program_id}")
                    # print(f"Error logs: {error_logs}")
                    program_to_error_logs[program_id].append( {
                        "error_logs": error_logs,
                        "cnt": cnt
                    })                     
            i += 3            
    return program_to_error_logs

def error_logs_to_error_types(program_to_error_logs):
    df_types = pd.read_csv("/data0/xiaoyez/Solana_Ecosystem/src/analyze/RQ2/output_fig/error_categorization.csv")
    for program_id, logs in program_to_error_logs.items():
        for log in logs:
            log["error_type"] = "Uncategorized"
            for column in df_types.columns:
                if log["error_logs"] in df_types[column].values:
                    log["error_type"] = column
                    break
    return program_to_error_logs

def plot_sankey_diagram(program_to_error_types):
    color_plates = ['rgba(31, 119, 180, 0.5)',  # Blue
          'rgba(255, 127, 14, 0.5)',  # Orange
          'rgba(44, 160, 44, 0.5)',   # Green
          'rgba(214, 39, 40, 0.5)',   # Red
          'rgba(148, 103, 189, 0.5)', # Purple
          'rgba(140, 86, 75, 0.5)',   # Brown
          'rgba(227, 119, 194, 0.5)', # Pink
          'rgba(127, 127, 127, 0.5)', # Gray
          'rgba(188, 189, 34, 0.5)',  # Yellow
          'rgba(23, 190, 207, 0.5)']  # Cyan
    node_color_plates = ['rgba(31, 119, 180, 0.7)',  # Blue
          'rgba(255, 127, 14, 0.7)',  # Orange
          'rgba(44, 160, 44, 0.7)',   # Green
          'rgba(214, 39, 40, 0.7)',   # Red
          'rgba(148, 103, 189, 0.7)', # Purple
          'rgba(140, 86, 75, 0.7)',   # Brown
          'rgba(227, 119, 194, 0.7)', # Pink
          'rgba(127, 127, 127, 0.7)', # Gray
          'rgba(188, 189, 34, 0.7)',  # Yellow
          'rgba(23, 190, 207, 0.7)']  # Cyan
    error_type_color = {
        'Price or Profit not met': 'rgba(44, 160, 44, 0.7)',   # Green, 
        'Invalid Status':'rgba(31, 119, 180, 0.7)',  # Blue, 
        'Out of funds': 'rgba(140, 86, 75, 0.7)',   # Brown,
        'Network Delay': 'rgba(23, 190, 207, 0.7)', # Cyan
        'Invalid Input Parameters': 'rgba(214, 39, 40, 0.7)',   # Red, 
        'Invalid Input Account': 'rgba(188, 189, 34, 0.7)',  # Yellow,
        'Out of Resource': 'rgba(148, 103, 189, 0.7)', # Purple, 
        'Program Logic Constraint Violation': 'rgba(255, 127, 14, 0.7)',  # Orange,
        'Program Runtime Error': 'rgba(127, 127, 127, 0.7)', # Gray,
        'Unknown': 'rgba(227, 119, 194, 0.7)', # Pink,
        'Uncategorized':' rgba(227, 119, 194, 0.7)', # Pink,,
    }
    label = []
    node_colors = []
    label.extend([top_failed_programs[program_id] for program_id in program_to_error_types.keys()])
    node_colors.extend([node_color_plates[i] for i, _ in enumerate(program_to_error_types.keys())])

    df_types = pd.read_csv("/data0/xiaoyez/Solana_Ecosystem/src/analyze/RQ2/output_fig/error_categorization.csv")
    label.extend(df_types.columns)
    print(df_types.columns)
    node_colors.extend([error_type_color[column] for i, column in enumerate(df_types.columns)])
    label.append("Uncategorized")
    
    
    source, colors, color_idx = [], [], 0
    for program_id, logs in program_to_error_types.items():
        idx = label.index(top_failed_programs[program_id])
        source.extend([idx] * len(logs))
        colors.extend([color_plates[color_idx]]*len(logs))
        color_idx += 1
    target = []
    for program_id, logs in program_to_error_types.items():
        for log in logs:
            idx = label.index(log["error_type"])
            target.append(idx)
    
    value = []
    for program_id, logs in program_to_error_types.items():
        for log in logs:
            value.append(log["cnt"])

    hovertemplate = (
        'Failed Txs: %{value:,.0f}<br>' +
        'Program Address: %{source.label}<br>' +
        'Error Type: %{target.label}<br>' +
        '<extra></extra>'
    )
    
    # Create the figure
    fig = go.Figure(data=[go.Sankey(
        node = dict(
                    thickness = 20,
            line = dict(color = "black", width = 0.5),
            label = label,
            color = node_colors
        ),
        link = dict(
            source = source,
            target = target,
            value = value,
            # color = colors,
            hovertemplate = hovertemplate
            # label = [f'{v}' for v in value], 
        )
    )])

    # Update layout
    fig.update_layout(
        # title_text="Error Types for Top failed programs",
        font_size=18,
        height=800,
        # hovermode = True
    )
    # fig.write_image("/data0/xiaoyez/Solana_Ecosystem/src/analyze/RQ3/output_fig/program_sankey_diagram.pdf", 
    #     width=1200, 
    #     height=800, 
    #     scale=2
    # )
    fig.write_image("/data0/xiaoyez/Solana_Ecosystem/src/analyze/RQ3/output_fig/program_sankey_diagram.png", scale=2) 
    # fig.write_html("/data0/xiaoyez/Solana_Ecosystem/src/analyze/RQ3/output_fig/program_sankey_diagram.html")


def test():
    # Define nodes and their indices
    companies = {
        "Google": 0, 
        "Amazon": 1, 
        "Microsoft": 2, 
        "Apple": 3, 
        "Samsung": 4, 
        "Huawei": 5, 
        "Meta": 6, 
        "Tencent": 7, 
        "Alibaba": 8
    }

    revenue_types = {
        "Consumer Electronics": 9,
        "E-commerce": 10, 
        "Ads": 11,
        "Cloud": 12,
        "Semiconductors": 13,
        "Software": 14,
        "Services": 15,
        "Telecommunications": 16,
        "Gaming": 17
    }

    # Define flows
    source = [0, 0, 0,  # Google flows
            1, 1, 1,  # Amazon flows
            2, 2, 2,  # Microsoft flows
            3, 3,     # Apple flows
            4, 4,     # Samsung flows
            5,        # Huawei flows
            6,        # Meta flows
            7,        # Tencent flows
            8]        # Alibaba flows

    target = [9, 10, 11,    # Targets for Google
            10, 12, 11,   # Targets for Amazon
            14, 12, 11,   # Targets for Microsoft
            9, 11,        # Targets for Apple
            9, 13,        # Targets for Samsung
            13,           # Target for Huawei
            11,           # Target for Meta
            17,           # Target for Tencent
            10]          # Target for Alibaba

    value = [50, 502, 363,  # Values for flows
            502, 150, 363,
            108, 150, 363,
            509, 363,
            509, 125,
            125,
            363,
            21,
            502]

    # Method 1: Color by company (source)
    company_colors = {
        "Google": "#4285F4",     # Google blue
        "Amazon": "#FF9900",     # Amazon orange
        "Microsoft": "#00A4EF",  # Microsoft blue
        "Apple": "#A2AAAD",      # Apple gray
        "Samsung": "#1428A0",    # Samsung blue
        "Huawei": "#FF0000",     # Huawei red
        "Meta": "#0668E1",       # Meta blue
        "Tencent": "#3AAD00",    # Tencent green
        "Alibaba": "#FF6A00"     # Alibaba orange
    }

    # Map colors to flows based on source company
    flow_colors_by_company = []
    for s in source:
        for company, idx in companies.items():
            if s == idx:
                flow_colors_by_company.append(company_colors[company])
    print(len(source), len(flow_colors_by_company))
    # Create the figure (using company-based colors)
    fig = go.Figure(data=[go.Sankey(
        node = dict(
            pad = 15,
            thickness = 20,
            line = dict(color = "black", width = 0.5),
            label = list(companies.keys()) + list(revenue_types.keys()),
            color = "lightgray"
        ),
        link = dict(
            source = source,
            target = target,
            value = value,
            color = flow_colors_by_company  # or use flow_colors_by_revenue for revenue-based coloring
        )
    )])

    # Update layout
    fig.update_layout(
        title_text="Top Revenue Sources for Tech Firms",
        font_size=12,
        height=600,
        paper_bgcolor='white',
        plot_bgcolor='white'
    )

    # Save to PNG
    fig.write_image("sankey_diagram.png", scale=2)
if __name__ == "__main__":
    program_to_error_logs = get_top_failed_program_error_logs()
    program_to_error_types = error_logs_to_error_types(program_to_error_logs)
    plot_sankey_diagram(program_to_error_types)
    # test()

# print(program_to_error_logs)