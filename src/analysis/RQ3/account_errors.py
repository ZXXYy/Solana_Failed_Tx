import time
import sys
import os
sys.path.append("/data0/xiaoyez/Solana_Ecosystem")
import json
import pymongo

import pandas as pd
from collections import defaultdict 
import plotly.graph_objects as go

from src.analysis.RQ1.initiators import get_top_failed_signers

def get_failed_log_for_signer(signers):
    myclient = pymongo.MongoClient("mongodb://localhost:27018/")
    mydb = myclient["solana"]
    txs_table = mydb["txs_one_year"]
    pipeline = [
         {
            "$match": {
                "error": { "$ne": None },
                "vote": { "$exists": False },
                "signer": { "$in": signers },
                # "block_id": { "$gte": 209292602, "$lte": 209302602 }
            }
        },
        {
            "$addFields": {
                "processedLogMessage": {
                    "$function": {
                        "body": """
                        function(logMessage, program) {
                            let matches = logMessage.match(/Program log: (.+?)\\n/g);
                            let i = matches? matches.length - 1: -1;
                            while(i>=0){
                                let log = matches ? matches[i].replace('Program log: ', '').trim() : '';
                                error_log_matches = log.match(/Error Message: (.+?)\\./); 
                                error_log_matches = error_log_matches ? error_log_matches : log.match(/Error: (.+?)(\\n|$)/);
                                error_log_matches = error_log_matches ? error_log_matches : log.match(/ERR: (.+?)(\\n|$)/);
                                if (error_log_matches) {  
                                    return program + '_' + error_log_matches[1].trim() ;
                                } else if(log.includes('panicked')) {
                                    return program + '_' + log;
                                } else if(log.includes('Sequence out of order')) {
                                    return  program + '_' + 'Sequence out of order';
                                } else if ('IOC order failed to meet minimum fill requirements'){
                                    return program + '_' + 'IOC order failed to meet minimum fill requirements'
                                } 
                                i--;
                            }
                            matches = logMessage.match(/Program (.+?) failed: custom program error: (.+?)\\n/);
                            if (matches){
                                return matches[1].trim()+'_'+matches[2].trim();
                            } else if (logMessage.match(/Program (.+?) failed: (.+?)\\n/)){
                                return program + '_' + logMessage.match(/Program (.+?) failed: (.+?)\\n/)[2].trim();
                            }
                            return logMessage;
                        }
                        """,
                        "args": ["$failedLogMessages", "$failedInstruction.program"],
                        "lang": "js"
                    }
                }
            }
        },
        {
            "$group": {
                "_id": {
                    "signer": "$signer",
                    "error_log": "$processedLogMessage"
                },
                "count": {
                    "$sum": 1
                }
            }
        },
    ]
    results = txs_table.aggregate(pipeline, allowDiskUse=True)
    error_logs = []
    results_list = list(results)
    # dump results to file
    with open(f"/data0/xiaoyez/Solana_Ecosystem/src/analyze/RQ3/output_fig/failed_log_for_signer_one_year.json", "w") as f:
        json.dump(results_list, f, indent=4)
    # for result in results:
    #     error_log = result['_id']['error_log']
    #     error_log = error_log[error_log.find('_')+1:]
    #     error_log = "Balance decreased" if "Balance decreased" in error_log else error_log
    #     flag = True
    #     for temp in error_logs:
    #         if temp["error_log"] == error_log:
    #             temp["error_cnt"] += result['count']
    #             flag = False
    #         break                 
    #     if flag:
    #         error_logs.append({
    #             "error_log": error_log,
    #             "error_cnt": result['count']
    #         })
    return error_logs

def get_failed_program_for_signer(signer):
    myclient = pymongo.MongoClient("mongodb://localhost:27018/")
    mydb = myclient["solana"]
    program_signer = mydb["program_signer"]
    program_signer.create_index([("signer", pymongo.ASCENDING)])
    print("finish creating index")
    pipeline = [
        {
            "$match": {
                "signer": signer
            }
        },
        {
            "$group": {
                "_id": "$program",
                "count": { "$sum": 1 }
            }
        },
        {
            "$sort": {
                "count": -1
            }
        }
    ]
    results = program_signer.aggregate(pipeline, allowDiskUse=True)
    programs = []
    for result in results:
        programs.append({
            "program": result['_id'],
            "program_cnt": result['count']
        })
    return programs

def get_program_error_statitsics():
    _,_, top_10_bots = get_top_failed_signers(is_bot=True)
    _,_, top_10_human = get_top_failed_signers(is_bot=False)

    signers = [bot['signer'] for bot in top_10_bots] + [human['signer'] for human in top_10_human]
    error_logs = get_failed_log_for_signer(signers)

def error_logs_to_error_types(account2statistic):
    df_types = pd.read_csv("/data0/xiaoyez/Solana_Ecosystem/src/analyze/RQ2/output_fig/error_categorization_revised.csv")
    for signer, statistics in account2statistic.items():
        for log in statistics['error']:
            log["error_type"] = "Uncategorized"
            for column in df_types.columns:
                if log["error_log"] in df_types[column].values:
                    log["error_type"] = column
                    break
    return account2statistic

def plot_sankey_diagram():
    bot_account2statistic = json.load(open(f"/data0/xiaoyez/Solana_Ecosystem/src/analyze/RQ3/output_fig/bot_error.json"))
    human_account2statistic = json.load(open(f"/data0/xiaoyez/Solana_Ecosystem/src/analyze/RQ3/output_fig/human_error.json"))

    human_account2statistic = error_logs_to_error_types(human_account2statistic)
    bot_account2statistic = error_logs_to_error_types(bot_account2statistic)

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
          'rgba(127, 127, 127, 0.7)', # Grayi
          'rgba(188, 189, 34, 0.7)',  # Yellow
          'rgba(23, 190, 207, 0.7)']  # Cyan
    error_type_color = {
        'Price or Profit not met': 'rgba(44, 160, 44, 0.7)',   # Green, 
        'Invalid Status':'rgba(31, 119, 180, 0.7)',  # Blue, 
        'Out of funds': 'rgba(140, 86, 75, 0.7)',   # Brown,
        'Validity Expiration': 'rgba(23, 190, 207, 0.7)', # Cyan
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
    label.extend([signer[:4] for signer in human_account2statistic.keys()])
    node_colors.extend([node_color_plates[i] for i, _ in enumerate(human_account2statistic.keys())])

    df_types = pd.read_csv("/data0/xiaoyez/Solana_Ecosystem/src/analyze/RQ2/output_fig/error_categorization.csv")
    label.extend(df_types.columns)
    print(df_types.columns)
    node_colors.extend([error_type_color[column] for i, column in enumerate(df_types.columns)])
    label.append("Uncategorized")
    
    label.extend([signer[:4] for signer in bot_account2statistic.keys()])
    node_colors.extend([node_color_plates[i] for i, _ in enumerate(bot_account2statistic.keys())])

    
    source, colors, color_idx = [], [], 0
    for signer, statistics in human_account2statistic.items():
        idx = label.index(signer[:4])
        source.extend([idx]*len(statistics["error"]))
    for signer, statistics in bot_account2statistic.items():
        for error_log in statistics['error']:
            idx = label.index(error_log['error_type'])
            source.append(idx)

    target = []
    for signer, statistics in human_account2statistic.items():
        for error_log in statistics['error']:
            idx = label.index(error_log['error_type'])
            target.append(idx)
    for signer, statistics in bot_account2statistic.items():
        idx = label.index(signer[:4])
        target.extend([idx]*len(statistics["error"]))

    value = []
    for signer, statistics in human_account2statistic.items():
        for error_log in statistics['error']:
            value.append(error_log["error_cnt"])
    for signer, statistics in bot_account2statistic.items():
        for error_log in statistics['error']:
            value.append(error_log["error_cnt"])
    
    

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
            # color = node_colors
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
    fig.write_image(f"/data0/xiaoyez/Solana_Ecosystem/src/analyze/RQ3/output_fig/account_sankey_diagram.png", scale=2) 

def plot_sankey_diagram_for_account_type(is_bot):
    account2statistic = json.load(open(f"/data0/xiaoyez/Solana_Ecosystem/src/analyze/RQ3/output_fig/{"bot" if is_bot else "human"}_error_one_year.json"))

    account2statistic = error_logs_to_error_types(account2statistic)

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
          'rgba(127, 127, 127, 0.7)', # Grayi
          'rgba(188, 189, 34, 0.7)',  # Yellow
          'rgba(23, 190, 207, 0.7)']  # Cyan
    error_type_color = {
        'Price or Profit not met': 'rgba(44, 160, 44, 0.7)',   # Green, 
        'Invalid Status':'rgba(31, 119, 180, 0.7)',  # Blue, 
        'Out of funds': 'rgba(140, 86, 75, 0.7)',   # Brown,
        'Validity Expiration': 'rgba(23, 190, 207, 0.7)', # Cyan
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
    label.extend([signer[:4] for signer in account2statistic.keys()])
    node_colors.extend([node_color_plates[i] for i, _ in enumerate(account2statistic.keys())])

    df_types = pd.read_csv("/data0/xiaoyez/Solana_Ecosystem/src/analyze/RQ2/output_fig/error_categorization_revised.csv")
    label.extend(df_types.columns)
    print(df_types.columns)
    node_colors.extend([error_type_color[column] for i, column in enumerate(df_types.columns)])
    label.append("Uncategorized")
    
    source, colors, color_idx = [], [], 0
    for signer, statistics in account2statistic.items():
        idx = label.index(signer[:4])
        source.extend([idx]*len(statistics["error"]))
    # for signer, statistics in bot_account2statistic.items():
    #     for error_log in statistics['error']:
    #         idx = label.index(error_log['error_type'])
    #         source.append(idx)

    target = []
    for signer, statistics in account2statistic.items():
        for error_log in statistics['error']:
            idx = label.index(error_log['error_type'])
            target.append(idx)
    # for signer, statistics in bot_account2statistic.items():
    #     idx = label.index(signer[:4])
    #     target.extend([idx]*len(statistics["error"]))

    value = []
    for signer, statistics in account2statistic.items():
        for error_log in statistics['error']:
            value.append(error_log["error_cnt"])
    # for signer, statistics in account2statistic.items():
    #     for error_log in statistics['error']:
    #         value.append(error_log["error_cnt"])
    
    

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
            # color = node_colors
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
    fig.write_image(f"/data0/xiaoyez/Solana_Ecosystem/src/analyze/RQ3/output_fig/{"bot" if is_bot else "human"}_sankey_diagram_one_year.png", scale=2) 

def patch():
    account2statistic = json.load(open(f"/data0/xiaoyez/Solana_Ecosystem/src/analyze/RQ3/output_fig/BEmUSjqs7mpgaSXw6QdrePfTsD8aQHbdtnqUxa63La6E_error_program.json"))
    errors = account2statistic["error"]
    new_errors = defaultdict(int)
    for error in errors:
        if "Balance decreased" in error["error_log"]:
            new_errors["Balance decreased"] += error["error_cnt"]
        else:
            new_errors[error["error_log"]] += error["error_cnt"]
    print(new_errors)
    account2statistic["error"] = [{"error_log": error, "error_cnt": cnt} for error, cnt in new_errors.items()]   
    print(account2statistic)
    json.dump(account2statistic, open(f"/data0/xiaoyez/Solana_Ecosystem/src/analyze/RQ3/output_fig/temp.json", "w"), indent=4)
                
def cal(is_bot):
    account2statistic = json.load(open(f"/data0/xiaoyez/Solana_Ecosystem/src/analyze/RQ3/output_fig/{"bot" if is_bot else "human"}_error_one_year.json"))
    account2statistic = error_logs_to_error_types(account2statistic)
    amm_cnt, invalid_status_cnt, price_profit_not_met_cnt, invalid_input_account_cnt, out_of_funds_cnt = 0,0,0,0,0
    total = 0
    for signer, statistics in account2statistic.items():
        for error in statistics['error']:
            total += error['error_cnt']
            if "The amm account owner is not match with this program" in error['error_log']:
                amm_cnt += error['error_cnt']
            if error['error_type'] == "Price or Profit not met":
                price_profit_not_met_cnt += error['error_cnt']
            if error['error_type'] == "Invalid Input Account":
                invalid_input_account_cnt += error['error_cnt']
            if error['error_type'] == "Invalid Status":
                invalid_status_cnt += error['error_cnt']
            if error['error_type'] == "Out of funds":
                out_of_funds_cnt += error['error_cnt']

    print(f"AMM: {amm_cnt}, Invalid Status: {invalid_status_cnt}, {invalid_status_cnt/total}")
    print(f"Price or Profit not met: {price_profit_not_met_cnt}, {price_profit_not_met_cnt/total}")
    print(f"Invalid Input Account: {invalid_input_account_cnt}, {invalid_input_account_cnt/total}")
    print(f"Out of funds: {out_of_funds_cnt}, {out_of_funds_cnt/total}")

def handle_failed_log_for_signer(is_bot):
    account2statistic = {}
    _,_, top_10_accounts = get_top_failed_signers(is_bot=is_bot)
    failed_log_for_signers = json.load(open(f"/data0/xiaoyez/Solana_Ecosystem/src/analyze/RQ3/output_fig/failed_log_for_signer_one_year.json"))

    for account in top_10_accounts:
        account2statistic[account['signer']] = {}
        account2statistic[account['signer']]["error"] = []       
        # programs = get_failed_program_for_signer(bot['signer'])
        # print(f"Programs: {programs}")
        for failed_log in failed_log_for_signers:
            if failed_log['_id']['signer'] == account['signer']:
                error_log = failed_log['_id']['error_log']
                account2statistic[account['signer']]["error"].append({
                    "error_log": error_log[error_log.find("_")+1:],
                    "error_cnt": failed_log['count']
                })
    # write  to file
    json.dump(account2statistic, open(f"/data0/xiaoyez/Solana_Ecosystem/src/analyze/RQ3/output_fig/{"bot" if is_bot else "human"}_error_one_year.json", "w"), indent=4)

if __name__ == "__main__":
    start_time = time.time()
    if not os.path.exists("/data0/xiaoyez/Solana_Ecosystem/src/analyze/RQ3/output_fig/failed_log_for_signer_one_year.json"):
        get_program_error_statitsics()
        print(f"Finish Bot stat:{time.time()-start_time}")
    else:
        print("Already get failed log for signer")

    if not os.path.exists("/data0/xiaoyez/Solana_Ecosystem/src/analyze/RQ3/output_fig/bot_error_one_year.json"):
        handle_failed_log_for_signer(True)
    if not os.path.exists("/data0/xiaoyez/Solana_Ecosystem/src/analyze/RQ3/output_fig/human_error_one_year.json"):
        handle_failed_log_for_signer(False)
    
    # patch()
    plot_sankey_diagram_for_account_type(True)
    plot_sankey_diagram_for_account_type(False)
    cal(True)
    print("-"*20)
    cal(False)

    print(f"Finish Bot stat:{time.time()-start_time}")