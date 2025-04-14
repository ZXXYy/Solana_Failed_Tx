import pymongo
import time
import re
import ast
import json
from collections import defaultdict
from tqdm import tqdm

import matplotlib.pyplot as plt

open_source_addresses = [
    "BGUMAp9Gq7iTEuizy4pqaxsTyUCBK68MDfK752saRPUY",
    "dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH",
    "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK", 
    "KLend2g3cP87fffoy8q1mQqGKjrxjC8boSyAYavgmjD",
    "cjg3oHmg9uuPsP8D6g29NWvhySJkdYdAo9D25PRbKXJ",
    "J1TnP8zvVxbtF5KFp5xRmWuvG9McnhzmBd9XGfCyuxFP",
    "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc",
    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",
    "ZETAxsqBRek56DhiGXrn75yj2NHU3aYUnxvHXpkf3aD",
    "PERPHjGBqRHArX4DySjwM6UJHiR3sWAatqfdBS2qQJu"
]

def get_failed_error_log_from_db():
    myclient = pymongo.MongoClient("mongodb://localhost:27018/")
    mydb = myclient["solana"]
    txs_table = mydb["txs_one_year"]
    pipeline = [
        {
            "$match": {
                "$and": [
                        { "error": { "$ne": None } },  # 匹配 error 不为 None
                        { "$expr": { "$eq": [ { "$type": "$vote" }, "missing" ] } },  # 检查 vote 字段是否不存在
                    ]
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
                "_id": "$processedLogMessage",
                "count": {
                    "$sum": 1
                }
            }
        },
        {
            "$sort": {
                "count": -1
            }
        },
        {
            "$out": "failed_error_log_cnt_one_year_v2"
        }
        # {
        #     "$project": {
        #         "processedLogMessage": 1,
        #         "_id": 0
        #     }
        # },
        # {
        #     "$limit": 500
        # }
    ]
    results = txs_table.aggregate(pipeline)
    # for result in results:
    #     print(result)

def get_failed_error_log_cnt_from_db():
    myclient = pymongo.MongoClient("mongodb://localhost:27018/")
    mydb = myclient["solana"]
    failed_errors = mydb["failed_error_log_cnt_one_year_v2"]
    results = list(failed_errors.find())
    new_results = defaultdict(int)
    # reduce key 
    for result in tqdm(results):
        if result['_id'].startswith('4ngnN8dA9sAf1sbz3m6qwquxbHkyzgXVpeTYcxKPtZuf_Balance decreased'):
            new_results['4ngnN8dA9sAf1sbz3m6qwquxbHkyzgXVpeTYcxKPtZuf_Balance decreased'] += result['count']
        elif result['_id'].startswith('DqhtFVXHQJ8mfHpMZ3rkYzCXrnX9U1We2L7CcdxU3EMb_panicked at'):
            new_results['DqhtFVXHQJ8mfHpMZ3rkYzCXrnX9U1We2L7CcdxU3EMb_panicked at'] += result['count']
        elif re.findall(r"GzxwDvhbNcKTt4LBez3k9CuKZfuq5N3mZKYkBTKn1nKX_final(:)? \d+ orig(:)? \d+",result['_id']):
            new_results['GzxwDvhbNcKTt4LBez3k9CuKZfuq5N3mZKYkBTKn1nKX_final NUM orig NUM'] += result['count']
        elif "Program 24Uqj9JCLxUeoC3hGfh5W3s9FM9uCHDS2SG3LYwBpyTi consumed" in result['_id'] and "Log truncated" in result['_id']:
            new_results['24Uqj9JCLxUeoC3hGfh5W3s9FM9uCHDS2SG3LYwBpyTi_Log truncated'] += result['count']
        elif "Program JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4 consumed" in result['_id'] and "Log truncated" in result['_id']:
            new_results['JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4_Log truncated'] += result['count']
        elif "Program ZETAxsqBRek56DhiGXrn75yj2NHU3aYUnxvHXpkf3aD consumed" in result['_id'] and "Log truncated" in result['_id']:
            new_results['ZETAxsqBRek56DhiGXrn75yj2NHU3aYUnxvHXpkf3aD_Log truncated'] += result['count']
        elif re.match(r"Program zDEXqXEG7gAyxb1Kg9mK5fPnUdENCGKzWrM21RMdWRq success", result['_id']) and "Log truncated" in result['_id']:
            new_results['zDEXqXEG7gAyxb1Kg9mK5fPnUdENCGKzWrM21RMdWRq_Program data: GmTE6l15n9/aszcnAON00Jksi/BswFAPMMYZviPQcz6t7a53BXPfB26QBLPjq0/srtRvDed45XtKVPqt1vrwHUYOUth0BY5GAYkBAAAAAAAAAACmbnj3/////wDW02kPAAAAOQUAAAAAAAAB_Log truncated'] += result['count']
        elif re.match(r"Program zDEXqXEG7gAyxb1Kg9mK5fPnUdENCGKzWrM21RMdWRq consumed|", result['_id']) and "Log truncated" in result['_id']:
            new_results['zDEXqXEG7gAyxb1Kg9mK5fPnUdENCGKzWrM21RMdWRq_Log truncated'] += result['count']
        elif "Program PhoeNiXZ8ByJGLkxNfZRnkUfjvmuYqLR89jjFHGqdXY consumed" in result['_id'] and "Log truncated" in result['_id']:
            new_results['PhoeNiXZ8ByJGLkxNfZRnkUfjvmuYqLR89jjFHGqdXY_Log truncated'] += result['count']
        elif "Program Eo7WjKq67rjJQSZxS6z3YkapzY3eMj6Xy8X5EQVn5UaB consumed" in result['_id'] and "Log truncated" in result['_id']:
            new_results['Eo7WjKq67rjJQSZxS6z3YkapzY3eMj6Xy8X5EQVn5UaB_Program data: UWzjvs3QCsTDo+89JAAAABP6JwAAAAAAg+ExFwAAAAAAAAAAAAAAAAAAAAAAAAAA_Log truncated'] += result['count']    
        elif "wormDTUJ6AWPNvk59vGQbDvGJmqbDTdgWgAqcLBCgUb_AlreadyInitialized" in result['_id']:
            new_results['wormDTUJ6AWPNvk59vGQbDvGJmqbDTdgWgAqcLBCgUb_AlreadyInitialized'] += result['count']
        elif "WnFt12ZrnzZrFZkt2xsNsaNWoQribnuQ5B5FrDbwDhD_AlreadyInitialized" in result['_id']:
            new_results['WnFt12ZrnzZrFZkt2xsNsaNWoQribnuQ5B5FrDbwDhD_AlreadyInitialized'] += result['count']
        elif result['_id'].startswith("4MangoMjqJ2firMokCjjGgoK8d4MXcrgL7XJaL3w6fVg_account profitability is mismatched; account a pnl is not positive"):
            new_results["4MangoMjqJ2firMokCjjGgoK8d4MXcrgL7XJaL3w6fVg_account profitability is mismatched; account a pnl is not positive"] += result['count']
        elif re.match(r"4MangoMjqJ2firMokCjjGgoK8d4MXcrgL7XJaL3w6fVg_perp order id not found on the orderbook;",result['_id']):
            new_results["4MangoMjqJ2firMokCjjGgoK8d4MXcrgL7XJaL3w6fVg_perp order id not found on the orderbook; could not find perp order with client order id NUM in user account"] += result['count']
        elif re.match(r"SAGEqqFewepDHH6hMDcmWy7yjHPpyKLDnRXKb3Ki8e6_panicked at 'ComputeBudgetInstruction::SetComputeUnitLimit must be at least 200000. Value: \d+', programs/sage/src/instructions/survey_data_unit/scan.rs:186:25", result['_id']):
            new_results["SAGEqqFewepDHH6hMDcmWy7yjHPpyKLDnRXKb3Ki8e6_panicked at 'ComputeBudgetInstruction::SetComputeUnitLimit must be at least 200000. Value: NUM', programs/sage/src/instructions/survey_data_unit/scan.rs:186:25"] += result['count']
        elif re.match(r"TWAPrdhADy2aTKN5iFZtNnkQYXERD9NvKjPFVPMSCNN_Could not find order in user account; client order id = \d+", result['_id']):
            new_results["TWAPrdhADy2aTKN5iFZtNnkQYXERD9NvKjPFVPMSCNN_Could not find order in user account; client order id = NUM"] += result['count']
        elif re.match(r"opnb2LAfJYbRMAHHvqjCwQxanZn7ReEHp1k81EohpZb_Order id not found on the orderbook; no order with id \d+, side Ask, component Fixed found on the orderbook", result['_id']):
            new_results["opnb2LAfJYbRMAHHvqjCwQxanZn7ReEHp1k81EohpZb_Order id not found on the orderbook; no order with id NUM, side Ask, component Fixed found on the orderbook"] += result['count']
        elif re.match(r"opnb2LAfJYbRMAHHvqjCwQxanZn7ReEHp1k81EohpZb_Order id not found on the orderbook; no order with id \d+, side Bid, component Fixed found on the orderbook", result['_id']):
            new_results["opnb2LAfJYbRMAHHvqjCwQxanZn7ReEHp1k81EohpZb_Order id not found on the orderbook; no order with id NUM, side Bid, component Fixed found on the orderbook"] += result['count']
        elif re.match(r"opnb2LAfJYbRMAHHvqjCwQxanZn7ReEHp1k81EohpZb_Could not find order in user account; client order id = \d+", result["_id"]):
            new_results["opnb2LAfJYbRMAHHvqjCwQxanZn7ReEHp1k81EohpZb_Could not find order in user account; client order id = NUM"] += result['count']
        elif re.match(r"ALqmkguAexGywkd4EVEWnd6uqctJxsFU1SrtH1rLB6bK_final \d+ orig \d+", result['_id']):
            new_results["ALqmkguAexGywkd4EVEWnd6uqctJxsFU1SrtH1rLB6bK_final NUM orig NUM"] += result['count']
        elif re.match(r"(.*)_exceeded CUs meter at BPF instruction #\d+", result['_id']):
            program_id = re.match(r"(.*)_exceeded CUs meter at BPF instruction #\d+", result['_id']).group(1)
            new_results[program_id + "_exceeded CUs meter at BPF instruction #NUM"] += result['count']
        elif re.match(r"(.*)_final: \d+ orig: \d+", result['_id']):
            program_id = re.match(r"(.*)_final: \d+ orig: \d+", result['_id']).group(1)
            new_results[program_id + "_final NUM orig NUM"] += result['count']
        elif re.match(r"(.*)_panicked at 'explicit panic'", result['_id']):
            program_id = re.match(r"(.*)_panicked at 'explicit panic'", result['_id']).group(1)
            new_results[program_id + "_panicked at 'explicit panic'"] += result['count']
        elif re.match(r"(.*)_panicked at 'called `Result::unwrap\(\)` on an `Err` value: \(\d+, \d+\)'", result['_id']):
            program_id = re.match(r"(.*)_panicked at 'called `Result::unwrap\(\)` on an `Err` value: \(\d+, \d+\)'", result['_id']).group(1)
            new_results[program_id + "_panicked at 'called `Result::unwrap()` on an `Err` value: (NUM, NUM)'"] += result['count']
        elif re.match(r"(.*)_panicked at 'range start index \d+ out of range for slice of length \d+'", result['_id']):
            program_id = re.match(r"(.*)_panicked at 'range start index \d+ out of range for slice of length \d+'", result['_id']).group(1)
            new_results[program_id + "_panicked at 'range start index NUM out of range for slice of length NUM'"] += result['count']
        elif re.match(r"(.*)_Instruction passed to inner instruction is too large \(\d+ > \d+\)", result['_id']):
            program_id = re.match(r"(.*)_Instruction passed to inner instruction is too large \(\d+ > \d+\)", result['_id']).group(1)
            new_results[program_id + "_Instruction passed to inner instruction is too large"] += result['count']
        elif re.match(r"(.*)_panicked at 'attempt to subtract with overflow'", result['_id']):
            program_id = re.match(r"(.*)_panicked at 'attempt to subtract with overflow'", result['_id']).group(1)
            new_results[program_id + "_panicked at 'attempt to subtract with overflow'"] += result['count']
        elif re.match(r"(.*)_panicked at 'Not a profitable route'", result['_id']):
            program_id = re.match(r"(.*)_panicked at 'Not a profitable route'", result['_id']).group(1)
            new_results[program_id + "_panicked at 'Not a profitable route'"] += result['count']
        elif re.match(r"(.*)_panicked at programs/pump/src/lib\.rs", result['_id']):
            program_id = re.match(r"(.*)_panicked at programs/pump/src/lib\.rs", result['_id']).group(1)
            new_results[program_id + "_panicked at programs/pump/src/lib.rs"] += result['count']
        elif re.match(r"(.*)_panicked at 'index out of bounds: the len is \d+ but the index is \d+'", result['_id']):
            program_id = re.match(r"(.*)_panicked at 'index out of bounds: the len is \d+ but the index is \d+'", result['_id']).group(1)
            new_results[program_id + "_panicked at 'index out of bounds: the len is NUM but the index is NUM'"] += result['count']
        elif re.match(r"program (.*) success", result['_id'].lower()):
            program_id = re.match(r"program (.*) success", result['_id'].lower()).group(1)
            new_results[program_id + "_success"] += result['count']
        elif re.match(r"(.*)_bank utilization has reached limit; deposits", result['_id']):
            program_id = re.match(r"(.*)_bank utilization has reached limit; deposits", result['_id']).group(1)
            new_results[program_id + "_bank utilization has reached limit; deposits"] += result['count']
        elif re.match(r"(.*)_panicked at 'old_price \d+ and new_price \d+ have a price difference >= \d+%'", result['_id']):
            program_id = re.match(r"(.*)_panicked at 'old_price \d+ and new_price \d+ have a price difference >= \d+%'", result['_id']).group(1)
            new_results[program_id + "_panicked at 'old_price NUM and new_price NUM have a price difference >= NUM%'"] += result['count']
        elif re.match(r"(.*)_incorrect number of health accounts; received \d+ accounts but expected \d+", result['_id']):
            program_id = re.match(r"(.*)_incorrect number of health accounts; received \d+ accounts but expected \d+", result['_id']).group(1)
            new_results[program_id + "_incorrect number of health accounts; received NUM accounts but expected NUM"] += result['count']
        elif re.match(r"(.*)_bank utilization has reached limit; vault_amount", result['_id']):
            program_id = re.match(r"(.*)_bank utilization has reached limit; vault_amount", result['_id']).group(1)
            new_results[program_id + "_bank utilization has reached limit; vault_amount"] += result['count']
        elif re.match(r"(.*)_token position does not exist; token index \d+ not found", result['_id']):
            program_id = re.match(r"(.*)_token position does not exist; token index \d+ not found", result['_id']).group(1)
            new_results[program_id + "_token position does not exist; token index NUM not found"] += result['count']
        elif re.match(r"(.*)_could not find perp order with id \d+ in user account", result['_id']):
            program_id = re.match(r"(.*)_could not find perp order with id \d+ in user account", result['_id']).group(1)
            new_results[program_id + "_could not find perp order with id NUM in user account"] += result['count']
        elif re.match(r"(.*)_an oracle does not reach the confidence threshold; getting oracle for bank with health account index \d+ and token index \d+", result['_id']):
            program_id = re.match(r"(.*)_an oracle does not reach the confidence threshold; getting oracle for bank with health account index \d+ and token index \d+", result['_id']).group(1)
            new_results[program_id + "_an oracle does not reach the confidence threshold; getting oracle for bank with health account index NUM and token index NUM"] += result['count']
        elif re.match(r"(.*)_panicked at 'slice index starts at \d+ but ends at \d+'", result['_id']):
            program_id = re.match(r"(.*)_panicked at 'slice index starts at \d+ but ends at \d+'", result['_id']).group(1)
            new_results[program_id + "_panicked at 'slice index starts at NUM but ends at NUM'"] += result['count']
        elif re.match(r"(.*)_panicked at 'called `Option::unwrap\(\)` on a `None` value'", result['_id']):
            program_id = re.match(r"(.*)_panicked at 'called `Option::unwrap\(\)` on a `None` value'", result['_id']).group(1)
            new_results[program_id + "_panicked at 'called `Option::unwrap()` on a `None` value'"] += result['count']
        elif re.match(r"(.*)_Custom program error: 0x\d+", result['_id']):
            program_id = re.match(r"(.*)_Custom program error: 0x.*", result['_id']).group(1)
            new_results[program_id + "_Custom program error: 0xNUM"] += result['count']
        elif re.match(r"(.*)_panicked at 'range end index \d+ out of range for slice of length \d+'", result['_id']):
            program_id = re.match(r"(.*)_panicked at 'range end index \d+ out of range for slice of length \d+'", result['_id']).group(1)
            new_results[program_id + "_panicked at 'range end index NUM out of range for slice of length NUM'"] += result['count']
        elif re.match(r"(.*)_Additional lamports spent: \d+", result['_id']):
            program_id = re.match(r"(.*)_Additional lamports spent: \d+", result['_id']).group(1)
            new_results[program_id + "_Additional lamports spent: NUM"] += result['count']
        elif "AnchorError(AnchorError { error_name:" in result['_id']:
            program_id = re.match(r"(.*)_.*AnchorError\(AnchorError { error_name:.*", result['_id']).group(1)
            #  error_msg: "RewardsAlreadyClaimed", error_origin:
            error_message = result['_id'].split("error_msg: ")[1].split(", error_origin:")[0]
            new_results[program_id + "_" + error_message] += result['count']
        elif "program_error: InvalidAccountData, error_origin: None, compared_values: None" in result['_id']:
            program_id = result['_id'].split('_')[0]
            new_results[program_id + "_InvalidAccountData"] += result['count']
        elif re.match(r"(.*)_panicked at (.*/)+.*", result['_id']):
            program_id = re.match(r"(.*)_panicked at (.*/)+.*", result['_id']).group(1)
            new_results[program_id + "_panicked at filepath"] += result['count']
        elif re.match(r"(.*)_panicked at (.*\\)+.*", result['_id']):
            program_id = re.match(r"(.*)_panicked at (.*\\)+.*", result['_id']).group(1)
            new_results[program_id + "_panicked at filepath"] += result['count']
        elif re.match(r"(.*)_0x(\d|[a-z]|[A-Z])+", result['_id']):
            program_id = re.match(r"(.*)_0x(\d|[a-z]|[A-Z])+", result['_id']).group(1)
            new_results[program_id + "_0xNUM"] += result['count']
        elif re.match(r"(.*)_panicked at 'amount_in is below the threshold value'", result['_id']):
            program_id = re.match(r"(.*)_panicked at 'amount_in is below the threshold value'", result['_id']).group(1)
            new_results[program_id + "_panicked at 'amount_in is below the threshold value'"] += result['count']
        elif re.match(r"(.*)_panicked at programs/looter-sol-helper/src/lib.rs", result['_id']):
            program_id = re.match(r"(.*)_panicked at programs/looter-sol-helper/src/lib.rs", result['_id']).group(1)
            new_results[program_id + "_panicked at programs/looter-sol-helper/src/lib.rs"] += result['count']
        elif re.match(r"(.*)_panicked at 'token: .* is not locked by .*'", result['_id']):
            program_id = re.match(r"(.*)_panicked at 'token: .* is not locked by .*'", result['_id']).group(1)
            new_results[program_id + "_panicked at 'token: NUM is not locked by NUM'"] += result['count']
        elif re.match(r"4MangoMjqJ2firMokCjjGgoK8d4MXcrgL7XJaL3w6fVg_could not find perp order with client order id \d+ in user account", result['_id']):
            new_results["4MangoMjqJ2firMokCjjGgoK8d4MXcrgL7XJaL3w6fVg_Could not find perp order with client order id NUM in user account"] += result['count']
        elif re.match(r"4MangoMjqJ2firMokCjjGgoK8d4MXcrgL7XJaL3w6fVg_deposit crosses the token's deposit limit; deposit limit exceeded: remaining", result['_id']):
            new_results["4MangoMjqJ2firMokCjjGgoK8d4MXcrgL7XJaL3w6fVg_deposit crosses the token's deposit limit; deposit limit exceeded: remaining"] += result['count']
        elif "AXRsZddcKo8BcHrbbBdXyHozSaRGqHc11ePh9ChKuoa1_panicked at 'Withdraw amount atoms:" in result['_id']:
            new_results["AXRsZddcKo8BcHrbbBdXyHozSaRGqHc11ePh9ChKuoa1_panicked at 'Withdraw amount atoms: NUM min_out_atoms: NUM', programs/raven/src/instructions/trade_exact_in.rs:221:5"] += result["count"]
        elif "AXRsZddcKo8BcHrbbBdXyHozSaRGqHc11ePh9ChKuoa1_panicked at 'health ratio:" in result['_id']:
            new_results["AXRsZddcKo8BcHrbbBdXyHozSaRGqHc11ePh9ChKuoa1_panicked at 'health ratio: NUM', programs/raven/src/instructions/trade_exact_in.rs:435:13"] += result["count"]
        elif "4MangoMjqJ2firMokCjjGgoK8d4MXcrgL7XJaL3w6fVg_bank vault has insufficent funds; bank vault does not have enough tokens" in result['_id']:
            new_results["4MangoMjqJ2firMokCjjGgoK8d4MXcrgL7XJaL3w6fVg_bank vault has insufficent funds; bank vault does not have enough tokens"] += result["count"]
        elif "4MangoMjqJ2firMokCjjGgoK8d4MXcrgL7XJaL3w6fVg_bank net borrows has reached limit - this is an intermittent error - the limit will reset regularly" in result["_id"]:
            new_results["4MangoMjqJ2firMokCjjGgoK8d4MXcrgL7XJaL3w6fVg_bank net borrows has reached limit - this is an intermittent error - the limit will reset regularly"] += result["count"]
        elif "4MangoMjqJ2firMokCjjGgoK8d4MXcrgL7XJaL3w6fVg_account profitability is mismatched; account b pnl is not negative" in result['_id']:
            new_results["4MangoMjqJ2firMokCjjGgoK8d4MXcrgL7XJaL3w6fVg_account profitability is mismatched; account b pnl is not negative"] += result["count"]
        elif "4MangoMjqJ2firMokCjjGgoK8d4MXcrgL7XJaL3w6fVg_an oracle is stale" in result['_id']:
            new_results["4MangoMjqJ2firMokCjjGgoK8d4MXcrgL7XJaL3w6fVg_an oracle is stale"] += result["count"]
        
        else:
            new_results[result['_id']] += result['count']
    # sort dict 
    # new_results = dict(sorted(new_results.items(), key=lambda item: item[1]))
    # sum up counts
    # total = sum(new_results.values())
    # for key, value in new_results.items():
    #     print(key, value, value/total)
    return new_results

def post_handle(error_logs):
    res = defaultdict(dict)
    total = 0
    for key, value in error_logs.items():
        if "0x1770" not in key:
            new_key = key[key.find('_')+1:]
        res[new_key][key[:key.find('_')]]=value
        total += value
    res = dict(sorted(res.items(), key=lambda item: sum(item[1].values()), reverse=True))
    print(f"total error types: {len(res)}")
    print(f"total transactions: {total}")
    temp = 0
    with open("/data0/xiaoyez/Solana_Ecosystem/src/analyze/RQ2/output_fig/failed_txs_one_year.log", 'w') as f:
        for key, value in res.items():
            count = sum(value.values())
            temp = count/total + temp
            # write to file
            f.write(f"{key}\n{value}\n{count/total:<{6}.{4}f} {temp:<{6}.{4}f}\n")
    print(len(res))
    temp = 0
    open_source_cnt = 0
    error_open_source_cnt = 0
    with open("/data0/xiaoyez/Solana_Ecosystem/src/analyze/RQ2/output_fig/failed_txs_one_year_count.log", 'r') as f:
        for key, value in res.items():
            for kk, vv in value.items():
                if kk in open_source_addresses:
                    open_source_cnt += vv
            count = sum(value.values())
            temp = count/total + temp
    item = 0 
    open_source_log, close_source_log = [], []      
    for key, value in res.items():
        flag = True
        for kk, vv in value.items():
            if kk in open_source_addresses:
                error_open_source_cnt += 1
                open_source_log.append(key)
                flag = False
                break
        if flag:
            close_source_log.append(key)
        item += 1
        if item > 173:
            break
    # write to file
    # with open("/data0/xiaoyez/Solana_Ecosystem/src/analyze/RQ2/output_fig/failed_txs_one_year_open_source_log.log", 'w') as f:
    #     for log in open_source_log:
    #         f.write(f"{log}\n")
    # with open("/data0/xiaoyez/Solana_Ecosystem/src/analyze/RQ2/output_fig/failed_txs_one_year_close_source_log.log", 'w') as f:
    #     for log in close_source_log:
    #         f.write(f"{log}\n")
    # print(len(res))
    # print(open_source_cnt, open_source_cnt/total)
    # print(error_open_source_cnt) 

def cal(error_count, top2_program):
    total_txs = 806468469
    total = sum(error_count.values())
    other = total -error_count[top2_program[0]] - error_count[top2_program[1]]
    print(f"total transactions: {total} {total/total_txs}")
    print(f"other amm error program: {other} {other/total_txs}")

    for key, value in error_count.items():
        print(key, value, value/total_txs)
    return total

def cals():
    top_total = 0
    amm = {'675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8': 302206484, '9uW2TqLyfYyrcNVrgCy4jPpqDKQoBZhXWypzzFxbixQE': 13945861, '3Bm3HukBbB1eREqrsS76wKBYB7MkCUznLrcevVoHzaqw': 162498, 'BURSTBqFQnPSTSNno3X3Stdx91yCS51J9MH7uCP1knEX': 95846, '3HJDg13GwvQPdrYQY21zougWty6f1X8tNouRrCDWrzKy': 58153, 'JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4': 9970, '4bfLZc1xx3NjpUV6vPWzsY6m8mz42rVVctTZ1CMd6WmJ': 902, 'Heg9dzyBM3BL8rkVcHrhfNoRm7RPn4wn3dCzhgfCfhYK': 495, '9y7vKvCd1P3N7R2g77rFoSVrLSvLAUCyPi4vMpXiuwnD': 459, 'E23vtNG2mhHZFWzCx73zYey8mzfsUm5HBWQ9oS9vUYkw': 454, 'Hq1x133jLiHYU45kN58tC8UUcDQ3rzDtUSNZkYKUk3ZR': 427, '4QABZet2bwGvajeRYPfBQtHyaRVZ12oTHvrsabZ213qC': 411, '8QxkA3bwq8Q3pL89S37iyrkv6VWjndzFAaRnVKjinXJN': 144}
    amm = dict(sorted(amm.items(), key=lambda item: item[1], reverse=True))
    top_total += cal(error_count = amm, top2_program = ['675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8', '9uW2TqLyfYyrcNVrgCy4jPpqDKQoBZhXWypzzFxbixQE'])
    print('='*16)

    slippage = {'JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4': 123829408, 'JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB': 21484425, 'MP1zz2HUAzL5P2uLR5nKaDSnxofh8VTZyk26NCewWzk': 81682, 'JUP2jxvXaqu7NQY1GmNF4m1vodw12LVXYxbFL2uJvfo': 17853, 'SQDS4ep65T869zMMBKyuUq6aD6EgTu8psMjkvj52pCf': 328, 'C1onEW2kPetmHmwe74YC1ESx3LnFEpVau6g2pg4fHycr': 72, 'GFXbUrN1NZu1Y5Shk5KLany2NAvX1oPiyfaPaNDpbxVF': 2, 'STAG3xkFMyVK3sRtQhipsKuLpRGbgospDpVdNyJqDpS': 2, 'AGGZ2djPDEvrbgiBTV3P8UoB8Zf1kGawkWd2eu553o44': 1, 'CzJLugPC4q4tsFyQuVoVwcfHE1VJgKdtGZrhXWFsKmc2': 1, 'RainEraPU5yDoJmTrHdYynK9739GkEfDsE4ffqce2BR': 1}
    slippage2 = {'6Q4Xu2sXxMLMhS2pSBJwhDrL5AMWGbrBT3yaN48kYX7G': 55317386, '675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8': 24538798, '3HJDg13GwvQPdrYQY21zougWty6f1X8tNouRrCDWrzKy': 69794, '4itxBe4qBAwhB9zpEAw31d7w8o7gTQscYpxhRtUemjF9': 49215, '8WhA6rGrFUj5JreBCBkgtkeKdiNR1BYKpwpPJwDoLP4B': 36704, '9uW2TqLyfYyrcNVrgCy4jPpqDKQoBZhXWypzzFxbixQE': 31061, '9HMC8WNeLUJi1UckuAFsgZqJ55KXivE7L6Q1A2vrEofB': 29716, 'YmirFH6wUrtUMUmfRPZE7TcnszDw689YNWYrMgyB55N': 11723, 'GZUZRLKRz4tMJnq6sgtSioHonhXQKDqdE5BMJKP1mV5z': 7048, '36z9tipgENz4wgt2XxnxXZVYQMtDPNw5UXeucYcH9dXv': 2962, 'E23vtNG2mhHZFWzCx73zYey8mzfsUm5HBWQ9oS9vUYkw': 2059, '4QABZet2bwGvajeRYPfBQtHyaRVZ12oTHvrsabZ213qC': 2018, 'Hq1x133jLiHYU45kN58tC8UUcDQ3rzDtUSNZkYKUk3ZR': 1958, 'Heg9dzyBM3BL8rkVcHrhfNoRm7RPn4wn3dCzhgfCfhYK': 1932, '9y7vKvCd1P3N7R2g77rFoSVrLSvLAUCyPi4vMpXiuwnD': 1914, '8QxkA3bwq8Q3pL89S37iyrkv6VWjndzFAaRnVKjinXJN': 734, '9MqJgoVX4rEQHv1RL2qJ2UWJRyapbsKoayhtUHrVG8hk': 527, 'AbgSLvGvuZQUWvE7oH8VEtDGBZaixYqkVrqWJbYmgKMB': 455, '5ZKhigaUWXa7GGhae8UdUjJtNJiMBLi3igGVstef3tHf': 310, 'EN1GMAXbcQF3ucku4wpxE45CKUaoBD3yiutrFqNfLfK7': 192, '3JmzqBoDLvNTPapBGCN7x23kTE5o7zkQ2fQhuyU3j9x6': 153, '3Qvevpr9VQp7ECWjAU186oiSGjMhDucjU32oSX8BfxGK': 85, '5bsvza81z1k2ZTyPXG6XuHmjPEtHP4xfkm8JUHEkGgns': 57, 'SQDS4ep65T869zMMBKyuUq6aD6EgTu8psMjkvj52pCf': 24, '4Ji3eRdwjCg2wuuJVbRBvqkPKz2xs4tchxQ4tZNhbUfs': 7, 's1owa2k7P2kkLEenZPKuGddWMVpy8Pt2oMVeBdtSHM6': 7, '44vxtqq7hx2UTcogDU4mraoPD2775QMUza4oBg29p9BX': 4, 'BSxRXGGfeB6ShDzosRjKjsXmgcNhDzxcgEB4Pxgt9TDi': 3, '2nAAsYdXF3eTQzaeUQS3fr4o782dDg8L28mX39Wr5j8N': 2, 'CtivAeeKA9QqwE8tWxwsohUoeDtwm9jnJdtYJMrWcXaD': 2}
    slippage3 = {'3J3HFc8jXxdvZQ73PeUPJmPdM2EKpKonzBaYACCXzqkv': 8304765}
    slippage = {**slippage, **slippage2, **slippage3}
    slippage = dict(sorted(slippage.items(), key=lambda item: item[1], reverse=True))
    top_total += cal(error_count = slippage, top2_program = ['JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4', '6Q4Xu2sXxMLMhS2pSBJwhDrL5AMWGbrBT3yaN48kYX7G'])
    print('='*16)

    # read from json file
    IOC = ast.literal_eval(open("/data0/xiaoyez/Solana_Ecosystem/src/analyze/RQ2/output_fig/IOC_error").read())
    IOC = dict(sorted(IOC.items(), key=lambda item: item[1], reverse=True))
    top_total += cal(error_count = IOC, top2_program = ['ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL', '6Q4Xu2sXxMLMhS2pSBJwhDrL5AMWGbrBT3yaN48kYX7G'])
    print('='*16)

    insufficient = {'675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8': 23348972, '6Q4Xu2sXxMLMhS2pSBJwhDrL5AMWGbrBT3yaN48kYX7G': 3195614, 'JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4': 2100584, '9uW2TqLyfYyrcNVrgCy4jPpqDKQoBZhXWypzzFxbixQE': 833715, 'routeUGWgWzqBWFcrCfv8tritsqukccJPu3q5GPP3xS': 247123, 'whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc': 228457, 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA': 192420, 'CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK': 72012, 'PhoeNiXZ8ByJGLkxNfZRnkUfjvmuYqLR89jjFHGqdXY': 69146, '8i97DHS9KPnG311fSY9yin4cyk9ZzkBjLXobyEFvtfKY': 26502, 'GUhB2ohrfqWspztgCrQpAmeVFBWmnWYhPcZuwY52WWRe': 22000, 'JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB': 20816, '8bvPnYE5Pvz2Z9dE6RAqWr1rzLknTndZ9hwvRE6kPDXP': 12735, '3Bm3HukBbB1eREqrsS76wKBYB7MkCUznLrcevVoHzaqw': 10928, 'jupoNjAxXgZ4rjzxzPMP4oxduvQsQtZzyknqvzYNrNu': 9023, 'YmirFH6wUrtUMUmfRPZE7TcnszDw689YNWYrMgyB55N': 7103, '9W959DqEETiGZocYWCQPaJ6sBmUzgfxXfqGeTEdp3aQP': 5728, '6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P': 5533, '4bfLZc1xx3NjpUV6vPWzsY6m8mz42rVVctTZ1CMd6WmJ': 3569, 'JVAp1DSLnM4Qh8qM1QasQ8x56ccb9S3DhbyEckybTF9': 3372, 'hemjuPXBpNvggtaUnN1MwT3wrdhttKEfosTcc2P9Pg8': 3176, '5bsvza81z1k2ZTyPXG6XuHmjPEtHP4xfkm8JUHEkGgns': 2658, 'BURSTBqFQnPSTSNno3X3Stdx91yCS51J9MH7uCP1knEX': 2353, 'TSWAPaqyCSx2KABk68Shruf4rp7CxcNi8hAsbdwmHbN': 1829, 'GZUZRLKRz4tMJnq6sgtSioHonhXQKDqdE5BMJKP1mV5z': 1771, 'DjVE6JNiYqPL2QXyCUUh8rNjHrbz9hXHNYt99MQ59qw1': 1641, 'FLUXubRmkEi2q6K3Y9kBPg9248ggaZVsoSFhtJHSrm1X': 1427, 'KLend2g3cP87fffoy8q1mQqGKjrxjC8boSyAYavgmjD': 1333, 'LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo': 1329, 'F5mYQ3f3B6UmBv84bumcdFrRjejh9skG2cQGHNab2aZZ': 1312, 'So1endDq2YkqhipRh3WViPa8hdiSpxWy6z3Z6tMCpAo': 1257, 'SAGEqqFewepDHH6hMDcmWy7yjHPpyKLDnRXKb3Ki8e6': 1222, 'BrdgN2RPzEMWF96ZbnnJaUtQDQx7VRXYaHHbYCBvceWB': 1026, 'SSwpMgqNDsyV7mAgN9ady4bDVu5ySjmmXejXvy2vLt1': 856, 'FLEET1qqzpexyaDpqb2DGsSzE2sDCizewCg9WjrA6DBW': 812, 'wormDTUJ6AWPNvk59vGQbDvGJmqbDTdgWgAqcLBCgUb': 749, 'LoanghCQGdUD7pSkqfagJ9Kdm6kgdE6CNpxgAxvvmTu': 736, 'cLmhcuG6pHbGHLzEKphgq6DBJvSiiY4h8D4kAppw7jd': 694, 'SwaPpA9LAaLfeLi3a68M4DjnLqgtticKg6CnyNwgAC8': 674, '8QxkA3bwq8Q3pL89S37iyrkv6VWjndzFAaRnVKjinXJN': 644, 'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb': 596, 'MFv2hWf31Z9kbCa1snEPYctwafyhdvnV7FZnsebVacA': 586, 'E23vtNG2mhHZFWzCx73zYey8mzfsUm5HBWQ9oS9vUYkw': 570, 'SW1TCH7qEPTdLsDHRgPuMQjbQxKdH2aBStViMFnt64f': 567, 'JUP2jxvXaqu7NQY1GmNF4m1vodw12LVXYxbFL2uJvfo': 549, 'Heg9dzyBM3BL8rkVcHrhfNoRm7RPn4wn3dCzhgfCfhYK': 522, '4QABZet2bwGvajeRYPfBQtHyaRVZ12oTHvrsabZ213qC': 519, 'Dooar9JkhdZ7J3LHN3A7YCuoGRUggXhQaG4kijfLGU2j': 514, 'STAKEkKzbdeKkqzKpLkNQD3SUuLgshDKCD7U8duxAbB': 496, 'Hq1x133jLiHYU45kN58tC8UUcDQ3rzDtUSNZkYKUk3ZR': 484, 'DvYekppGNjU9Euvn8ts4fmmnDt3p9J7yQmpmCmzawY2W': 458, '9y7vKvCd1P3N7R2g77rFoSVrLSvLAUCyPi4vMpXiuwnD': 427, 'opnb2LAfJYbRMAHHvqjCwQxanZn7ReEHp1k81EohpZb': 393, 'AbgSLvGvuZQUWvE7oH8VEtDGBZaixYqkVrqWJbYmgKMB': 392, 'M2mx93ekt1fmXSVkTrUL9xVFHkmME8HTUi5Cyc5aF7K': 392, 'NeonVMyRX5GbCrsAHnUwx1nYYoJAtskU1bWUo6JGNyG': 387, '3JmzqBoDLvNTPapBGCN7x23kTE5o7zkQ2fQhuyU3j9x6': 384, '3FVJYE7sVjbojTZ8ZHwm4TY87RJ9hdPiii7QqNeC2keV': 365, 'MP1zz2HUAzL5P2uLR5nKaDSnxofh8VTZyk26NCewWzk': 365, '2eEso2sAipRHNZ54d4fRJyeC6mVJq73F5mvsL1wZb3tp': 357, '5ocnV1qiCgaQR8Jb8xWnVbApfaygJ8tNoZfgPwsgx9kx': 355, '6LtLpnUFNByNXLyCoK9wA2MykKAmQNZKBdY8s47dehDc': 348, 'DCA265Vj8a9CEuX1eb1LWRnDT7uK6q1xMipnNyatn23M': 343, '9HMC8WNeLUJi1UckuAFsgZqJ55KXivE7L6Q1A2vrEofB': 336, 'voTpe3tHQ7AjQHMapgSue2HJFAh2cGsdokqN3XqmVSj': 250, 'LiquGRWGrp8JKspo8zDDu6qpRmX1p6U3PX2USqiE1eg': 230, 'EUd2qdzRyLq7t6mfsXQPSgf2nFqK7UcMRdEk34ePcDTF': 229, 'Eo7WjKq67rjJQSZxS6z3YkapzY3eMj6Xy8X5EQVn5UaB': 223, '8f2VBmoovE4f6JpQ3G8pLLKnuDpcdytszFwL7bP7iQGb': 222, 'SPoo1Ku8WFXoNDMHPsrGSTSG1Y47rzgn41SLUNakuHy': 208, '9yL9r9PcFfX3QM78noAyAscZekQue7djcKaxXDebaR1o': 207, '4MangoMjqJ2firMokCjjGgoK8d4MXcrgL7XJaL3w6fVg': 193, 'TMzXzV3VwPvrhZLBZQSAmthKYJXYbxcS3YvyEE9jsYv': 180, 'ELEMisgsfkmp58w1byRvrdpGG1HcapQoCrmMJeorBCxq': 179, '2L2pi4nR5xShAta21iFaYezXBUgNBh3kuLX8AtXmjufK': 161, '3HJDg13GwvQPdrYQY21zougWty6f1X8tNouRrCDWrzKy': 161, 'GovER5Lthms3bLBqWub97yVrMmEogzX7xNjdXpPPCVZw': 161, 'EMnmGvrgKJhYCk2HCbUQfSXLDjdCjv3FAfdKcNz8A9Kr': 153, '7Zb1bGi32pfsrBkzWdqd4dFhUXwp5Nybr1zuaEwN34hy': 140, 'HYzrD877vEcBgd6ySKPpa3pcMbqYEmwEF1GFQmvuswcC': 122, 'Bt2WPMmbwHPk36i4CRucNDyLcmoGdC7xEdrVuxgJaNE6': 118, 'PADWBS1VeV1LWsY6nciu6dRZjgSmUH2iPsUpHFVz7Wz': 118, 'traderDnaR5w6Tcoi3NFm53i48FTDNbGjBSZwWXDRrg': 114, 'credMBJhYFzfn7NxBMdU4aUqFggAjgztaCcv2Fo6fPT': 108, '3GRE3mhckAosTkYXfVvHm5WrW1AxK4aKp8LfoXLxEUYs': 96, 'APR1MEny25pKupwn72oVqMH4qpDouArsX8zX4VwwfoXD': 95, 'WnFt12ZrnzZrFZkt2xsNsaNWoQribnuQ5B5FrDbwDhD': 93, 'A21cXTVY8nTYaMBYWLWfAWkFoVNtru25byEBHeBFLopt': 91, 'HvRgaJSpcV9nZoutmR9c28168wNpnXDG3XESRXxS8ExU': 90, 'E74bvE68HWB2bsdRiFdX55gSHDG7wWHhy8DhfjQs3iyB': 78, 'gateVwTnKyFrE8nxUUgfzoZTPKgJQZUbLsEidpG4Dp2': 77, 'GATEp6AEtXtwHABNWHKH9qeh3uJDZtZJ7YBNYzHsX3FS': 76, 'nosScmHY2uR24Zh751PmGj9ww9QRNHewh9H59AfrTJE': 71, 'EhhTKczWMGQt46ynNeRX1WfeagwwJd7ufHvCDjRxjo5Q': 69, 'PERPHjGBqRHArX4DySjwM6UJHiR3sWAatqfdBS2qQJu': 64, 'CQ36xjMHgmgwEM1yvJYUWg3YxMvzwM4Mntn6vZrMk86z': 57, '2KehYt3KsEQR53jYcxjbQp2d2kCp4AkuQW68atufRwSr': 56, 'HyaB3W9q6XdA5xwpU4XnSZV94htfmbmqJXZcEbRaJutt': 56, 'GLoB4ZdemYP4msGvQq8NwYDmwdUyNtZ8GPjgMhR1fhBK': 55, '36z9tipgENz4wgt2XxnxXZVYQMtDPNw5UXeucYcH9dXv': 54, '9HbAjAMbq4tYPS49tLpLUmueNJwAECnaLr2FrKfTPgic': 53, 'SSwapUtytfBdBn1b9NUGG6foMVPtcWgpRU32HToDUZr': 53, 'hvsrNC3NKbcryqDs2DocYHZ9yPKEVzdSjQG6RVtK1s8': 52, 'MLENdNkmK61mGd4Go8BJX9PhYPN3azrAKRQsAC7u55v': 51, 'FLASH6Lo6h3iasJKWDs2F8TkW2UKf3s15C8PMGuVfgBn': 49, 'dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH': 49, 'src5qyZHqTqecJV4aY6Cb6zDZLMDzrDKKezs22MPHr4': 44, 'DuALd6fooWzVDkaTsQzDAxPGYCnLrnWamdNNTNxicdX8': 43, 'AECpbyv5BG7f7Ez9A3ZfKtGQUwbaeGPJng4tNDpKcwuY': 39, 'mmm3XBJg5gk8XJxEKBvdgptZz6SgK4tXvn36sodowMc': 36, '3J3HFc8jXxdvZQ73PeUPJmPdM2EKpKonzBaYACCXzqkv': 35, 'bidoyoucCtwvPJwmW4W9ysXWeesgvGxEYxkXmoXTaHy': 34, 'BSwp6bEBihVLdqJRKGgzjcGLHkcTuzmSo1TQkHepzH8p': 32, '3parcLrT7WnXAcyPfkCz49oofuuf2guUKkjuFkAhZW8Y': 31, 'DHNgWG9EzHGCQjt19Gs8Zsu92y6QaAN3AiFyAGfCGLS': 30, '7oyG4wSf2kz2CxTqKTf1uhpPqrw9a8Av1w5t8Uj5PfXb': 29, 'MERLuDFBMmsHnsBPZw2sDQZHvXFMwp8EdjudcU2HKky': 29, 'SQDS4ep65T869zMMBKyuUq6aD6EgTu8psMjkvj52pCf': 29, '5ZKhigaUWXa7GGhae8UdUjJtNJiMBLi3igGVstef3tHf': 27, 'FarmqiPv5eAj3j1GMdMCMUGXqPUvmquZtMy86QH6rzhG': 27, '2WJi4LWK47iukCDz4ecZ54ne5RaMnaj6BX3WewGLjBgJ': 26, '7rC6jPZVrN6cMRdTZ6mWfYm1fL722jnzZQ3rGQGKBSon': 26, 'ADsjv1Z5C3cNc7XbhvvXnMJMNMyJ2VMo1ejpq9Tf7nRA': 25, 'CtivAeeKA9QqwE8tWxwsohUoeDtwm9jnJdtYJMrWcXaD': 25, 'EJqwFjvVJSAxH8Ur2PYuMfdvoJeutjmH6GkoEFQ4MdSa': 24, 'FqGg2Y1FNxMiGd51Q6UETixQWkF5fB92MysbYogRJb3P': 23, 'STAKEr4Bh8sbBMoAVmTDBRqouPzgdocVrvtjmhJhd65': 22, 'stakeY8fAquw5iNrTuYXDHuoBUCWqNMpHvcCtNaLyhz': 22, '24Uqj9JCLxUeoC3hGfh5W3s9FM9uCHDS2SG3LYwBpyTi': 20, 'stkitrT1Uoy18Dk1fTrgPw8W6MVzoCfYoAFT4MLsmhq': 20, 'VoteMBhDCqGLRgYpp9o7DGyq81KNmwjXQRAHStjtJsS': 19, 'jCebN34bUfdeUYJT13J1yG16XWQpt5PDx6Mse9GUqhR': 19, 'D7f2m4qFfAP1osnsJrU5r2xbXuqfF1Doi38A8GbgAovd': 18, '5quBtoiQqxF9Jv6KYKctB59NT3gtJD2Y65kdnB1Uev3h': 17, '6HW8dXjtiTGkD4jzXs7igdFmZExPpmwUrRN5195xGup': 16, 'FC81tbGt6JWRXidaWYFXxGnTk4VgobhJHATvTRVMqgWj': 15, 'FarmsPZpWu9i7Kky8tPN37rs2TpmMrAZrC7S7vJa91Hr': 15, '3gHZaQrR1pDfNHodJydGZ3MCnMVD3BtEd9uNAAnDY2vr': 14, 'F96ZqjQ88f8cvXoJ2oK8x13BEagMBTXxhHP7PbJDBs2': 14, 'SNPRohhBurQwrpwAptw1QYtpFdfEKitr4WSJ125cN1g': 14, '5LPsToGvb8uD7MYLw7YNpUhszNuDPNQ3nmFGhWsxHATv': 12, '7QhquPrKnco5srDqaqTZf5VhrMCPYCrzoZrQU7BTzQLA': 12, 'MEXkeo4BPUCZuEJ4idUUwMPu4qvc9nkqtLn3yAyZLxg': 12, 'Print1Bbd4pf6MQboCh4vQZtLgxtqcxdXsnWu2SCfeV': 12, 'TCMPhJdwDryooaGtiocG1u3xcYbRpiJzb283XfCZsDp': 12, '4Ji3eRdwjCg2wuuJVbRBvqkPKz2xs4tchxQ4tZNhbUfs': 11, '8SggVQERk6p5G1Rp1JmfFog1Ud8KJHAenS7d53ZsoixS': 11, 'AX1qheGkSFj9aboYpki3rbviREfcb3PS6VAk4VPG31wF': 11, 'DEGNpUs8DhLSdDiU25BAmCQn2U6eN8nMAYwbLb41BPqY': 11, '1oanfPPN8r1i4UbugXHDxWMbWVJ5qLSN5qzNFZkz6Fg': 10, '2nAAsYdXF3eTQzaeUQS3fr4o782dDg8L28mX39Wr5j8N': 10, 'B4WsnJUukmjdSWK37CrWpkJABwm3HB1dLqJQFHQVsoSa': 10, 'FANGqNNwg2FbMgagvaQ914PN1D6i4eRxSz4PncwfX57j': 10, 'nosJhNRqr2bc9g1nfGDcXXTXvYUmxD4cVwy2pMWhrYM': 10, '4bcFeLv4nydFrsZqV5CgwCVrPhkQKsXtzfy2KyMz7ozM': 9, 'AzHrwdCsEZotAjr7sjenHrHpf1ZKYoGBP6N7HVhEsyen': 9, 'Book8kgaqG4UowjwDZXZcTfPyEjmzmU1zst8ZDqTqiDN': 9, 'EXBuYPNgBUXMTsjCbezENRUtFQzjUNZxvPGTd11Pznk5': 9, 'FarmuwXPWXvefWUeqFAa5w6rifLkq5X6E8bimYvrhCB1': 9, 'GTavkffQHnDKDH36YNFpk7uxwHNseTRo24tV4HGC8MNY': 9, 'R2y9ip6mxmWUj4pt54jP2hz2dgvMozy9VTSwMWE7evs': 9, 'jtogvBNH3WBSWDYD5FJfQP2ZxNTuf82zL8GkEhPeaJx': 9, 'sphnxz9DeFYmrTzGgb1UiG8nZsmjR3yEK8N8Bz8TT6f': 9, 'C1onEW2kPetmHmwe74YC1ESx3LnFEpVau6g2pg4fHycr': 8, 'CLMM9tUoggJu2wagPkkqs9eFG4BWhVBZWkP1qv3Sp7tR': 8, 'ArmN3Av2boBg8pkkeCK9UuCN9zSUVc2UQg1qR2sKwm8d': 7, 'BtDDM9Nve5JXUVvDg8wmLDVwzgGB8pJ6oum4fGRKM8Av': 7, 'CTMAxxk34HjKWxQ3QLZK1HpaLXmBveao3ESePXbiyfzh': 7, 'suMmgdsFnvM9pFBLiSQwAzgMKBqUtEMgsYvoe51eJ3N': 7, '82yxjeMsvaURa4MbZZ7WZZHfobirZYkH1zF8fmeGtyaQ': 6, '8TqqugH88U3fDEWeKHqBSxZKeqoRrXkdpy3ciX5GAruK': 6, '8w2oEVNHCgVGsLv2Ynmrs4vuuuMssTDEGJQr8DF4Xcpd': 6, 'AvqeyEDqW9jaBi7yrRA6AxJtLbMzRY9NX75HuPTMoS4i': 6, 'DgomLMaYWFhZiooP3gQJRUPEmgGaptGcFjU2kxP4yAg7': 6, 'DqhtFVXHQJ8mfHpMZ3rkYzCXrnX9U1We2L7CcdxU3EMb': 6, 'spinyGC8jAEWF44xaefPc8XCW4fACRshZrzgBPKZ8K6': 6, '3ttPX3DrJfdxxXbFXBaBaiVM9KAo3nFx2HU84AreCtBj': 5, '8888FTjdEYxJtcdqnEzEoNGhyrDivDLcS7KWWWHrdwoL': 5, '8LPjGDbxhW4G2Q8S6FvdvUdfGWssgtqmvsc63bwNFA7E': 5, '8tBcmZAMNm11DuGAS2r6PqSA3CKt72amoz8bVj14xRiT': 5, 'CUbkXMRWxumGzDwf43ysyFm3da77JRuUqLF1bmW4tGoZ': 5, 'SFarmWM5wLFNEw1q5ofqL7CrwBMwdcqQgK6oQuoBGZJ': 5, 'SSwpkEEcbUqx4vtoEByFjSkhKdCT862DNVb52nZg1UZ': 5, 'TLoCKic2wGJm7VhZKumih4Lc35fUhYqVMgA4j389Buk': 5, 'dst5MGcFPoBeREFAA5E3tU5ij8m5uVYwkzkSAbsLbNo': 5, 'proxLVSjzcEWgRTK7WwbRZFnkhbUNHG5dwNMvY2a9JK': 5, '5ezsSN6bd3Uec6jrJHSjwycbVyqry19EWQD4r7koAYjt': 4, '8WhA6rGrFUj5JreBCBkgtkeKdiNR1BYKpwpPJwDoLP4B': 4, '9ehXDD5bnhSpFVRf99veikjgq8VajtRH7e3D9aVPLqYd': 4, 'AEauWRrpn9Cs6GXujzdp1YhMmv2288kBt3SdEcPYEerr': 4, 'EfuseVF62VgpYmXroXkNww8qKCQudeHAEzczSAC7Xsir': 4, 'PBondDFu4LkX2iw1ozEvdhxv5CtmY7mzLRa8t8D75di': 4, 'SMPLecH534NA9acpos4G6x7uf3LWbCAwZQE9e8ZekMu': 4, 'Stk5NCWomVN3itaFjLu382u9ibb5jMSHEsh6CuhaGjB': 4, '6AzuBKDsR88vinh399HV5v7fgB1eZyoYwQ3PmdYqFRZG': 3, 'AMM55ShdkoGRB5jVYPjWziwk8m5MpwyDgsMWHaMSQWH6': 3, 'DS2Sj6NtroGYs2Qgda299j8U1gYu1LosZByKHor1pr3s': 3, 'DSwpgjMvXhtGn6BsbqmacdBZyfLj6jSWf3HJpdJtmg6N': 3, 'Ehqoimb4ZMEuroKSkRKC97cFHNzzkUnMopYvdTkivuKy': 3, 'LLoc8JX5dLAMVzbzTNKG6EFpkyJ9XCsVAGkqwQKUJoa': 3, 'Pinks8fXRcJ8EpNjK4vCf7saJ5hFeP9zRXGPwZrTukQ': 3, 'SDX1KCXoCUv49n2DQKmVy6XThqbHpx2jXdGBXDT1npp': 3, 'STAKEGztX7S1MUHxcQHieZhELCntb9Ys9BgUbeEtMu1': 3, 'iiXve1vzfub4K6HLvppcmWS5HzafNAFztCoSdSCFvJt': 3, 'tsP1jf31M3iGNPmANP3ep3iWCMTxpMFLNbewWVWWbSo': 3, 'vAuLTsyrvSfZRuRB3XgvkPwNGgYSs9YRYymVebLKoxR': 3, '13uxuLoQHvpp1K1571WcgoTYEV4Ys5ni7LqjBZiTmNNx': 2, '26LU856fqQXuGdWdMuqALMVeeazCvbGrm5v7oDYBdzBc': 2, '3BUZXy9mPcsSCoxJQiBu2xxpMP6HEvFMZbaL5CAWwLUf': 2, '3vxKRPwUTiEkeUVyoZ9MXFe1V71sRLbLqu1gRYaWmehQ': 2, '3wVzFJf6hMWgwY8hcZS9EBFTmubTTbUuPxAATR3MxeXf': 2, '4adD2DpsCqsVdDCBHo9DxHqmqqLtsuVZv5fUE3y72hYf': 2, '5FVv4vXjWxenXoyGreTVXvqNoNWVnDrCCZnQPfvynhbj': 2, '6F3N8a6fccRb8HxnPv3T2LudFmJk6VBy7MiQCJPUUo6a': 2, '9DJuDApinVT5GdhBGzZxqnzVyc1uHW4kussocZVZ8Wr8': 2, '9Ef7uzrdsFCjb3jCqR9YERTKAKnmpxj8QMRGKED1Csq5': 2, 'Auc6pav58pHNg91c9fJqLwodaya6yEaJuzGtNHnPC1eH': 2, 'BBbD1WSjbHKfyE3TSFWF6vx1JV51c8msKSQy4ess6pXp': 2, 'BMrafdefSrPWCwxgiKsRURz7uM3vd8maZFga6qCQDXBB': 2, 'CJsLwbP1iu5DuUikHEJnLfANgKy6stB2uFgvBBHoyxwz': 2, 'CSwAp3hdedZJBmhWMjv8BJ7anTLMQ2hBqKdnXV5bB3Nz': 2, 'EMK3JL1yZdNJUq5h2m4qLuQWibLSQGrAJqUpWFoDH22b': 2, 'Gamba2hK6KV3quKq854B3sQG1WMdq3zgQLPKqyK4qS18': 2, 'GateFzR5Q7nepBDKDnpJppdT1eenLBfXWcUNfMZAExcc': 2, 'HWSTVuDSWQpbu8QDYsxEZZ6qMULGQCuB4XCaZgbvZjvU': 2, 'HeQTtHWw83MhXGQXgWdQdFKbwhRuNDyRcTo648WsXHnT': 2, 'Port7uDYB3wk6GJAw4KT1WpTeMtSu9bTcChBHkX2LfR': 2, 'QMNeHCGYnLVDn1icRAfQZpjPLBNkfGbSKRB83G5d8KB': 2, 'RoTom5BFr7M1K5cNwwLEjCVemqvJZpjGwQnFvi7GgHA': 2, 'Yt3A8KLfo7JEz8RGHw2zbaQE6MVcf9duKmb24dgXbsD': 2, 'rafxXxjw9fkAuQhCJ1A4gmX1oqgvRrSeXyRPUE9K2Yx': 2, 'srmv4uTCPF81hWDaPyEN2mLZ8XbvzuEM6LsAxR8NpjU': 2, 'stabmHGCsn8BxUqunRpq5x1kwCQzx2ACX5RZqGJLoXG': 2, 'zF2vSz6V9g1YHGmfrzsY497NJzbRr84QUrPry4bLQ25': 2, '28yMrqNvkZZ382KvGEMtJZvTLdrCBjhXjMfj1gFxgHFc': 1, '2RbwYVj8gmYf8TRNukd34fGJgT7X4X4K3t6gLGwJkNQD': 1, '2jmux3fWV5zHirkEZCoSMEgTgdYZqkE9Qx2oQnxoHRgA': 1, '3Qvevpr9VQp7ECWjAU186oiSGjMhDucjU32oSX8BfxGK': 1, '3puRp4bBPqDyBJuumc4Nwrv5W699kCZpmoTaQQKaobJh': 1, '4Q6WW2ouZ6V3iaNm56MTd5n2tnTm4C5fiH8miFHnAFHo': 1, '4yx1NJ4Vqf2zT1oVLk4SySBhhDJXmXFt88ncm4gPxtL7': 1, '6ueDsmj2cs9EQjfoLaGoiUKDk6f8yVhQib3EH9V41vvq': 1, '777vJPi4v1Ws7uDLfSNjEgs9NGq5nudyWjDUhsxdYHJd': 1, '7t6mC5ZJ7KH4nK29MMTfkhRN8cBVPiccGTLZjbqyDME9': 1, '7vxeyaXGLqcp66fFShqUdHxdacp4k4kwUpRSSeoZLCZ4': 1, '8F2VM13kdMBaHtcXPHmArtLueg7rfsa3gnrgGjAy4oCu': 1, '9JcNgNMPGSbjLhuXtoVd6e81n1g1r1ZXUon2gzF5XSyr': 1, '9aHEyxgFhfYqFTUhhBYb6VCz1zUS3sgQx45hMeubSoRZ': 1, 'A7kmu2kUcnQwAVn8B4znQmGJeUrsJ1WEhYVMtmiBLkEr': 1, 'Aza2jW4mjqyt8HtSLCwDTJWGJ1mRDjMQTQoiNTH6E32r': 1, 'BAheYL427Xw7q8RaGo981sfRoPuimwQXNabszngeucPM': 1, 'BGhgJ11yuYzU6wY9Wmt76edSPkPogCDQfMQbv6VQqHZq': 1, 'BYb5Hn9ftJFRhNaSWPWGE8ZJsse2JoJkmnhDp1nneeYG': 1, 'BrGZWHLx2VJ1VcFzsvi55rHNzawLWqMVaxivDDQx13Cb': 1, 'BtR62EkmumJNek65XvGcjYeWdSER1BjMSbfpngB5URnL': 1, 'CcLfuVMgNPbMiyLUJ4FBBrXc53rie3wy59MnVAkJrN8j': 1, 'DEbrdGj3HsRsAzx6uH4MKyREKxVAfBydijLUF3ygsFfh': 1, 'DFNDhXHGsTqh5uWBQjLPRyxd7GkbNrUJWnebqCRzWv32': 1, 'DYF7B5yXyeyGcBhKGqqtYoQqDDDEaHAicg3tNpYy4DZS': 1, 'DpnKE9Zo63YU73L5HJfrao6XVfcQHWeuTwSV6facfDhY': 1, 'F6HpVcR4nx28piV4GqTYdJ2vHDejjeE2npjmQ9PHxhaQ': 1, 'FC4eXxkyrMPTjiYUpp4EAnkmwMbQyZ6NDCh1kfLn6vsf': 1, 'FL3X2pRsQ9zHENpZSKDRREtccwJuei8yg9fwDu9UN69Q': 1, 'FtryBRW5XzhHd6Z9ghHnYUM35BqhaFbukM6HUBT1peUo': 1, 'GSnSv5PMGDLdU6SZ48rHq5dVBUTz6rtjj2pfWTAnT587': 1, 'GXnFYETRr9fRRF9CSRaXGHb5LJ5DGxdTL54BvmHxjNeC': 1, 'GaXaa2UEMKqyySjGFctngPwb4ufvRZSiAeeDPtSjjyCf': 1, 'HEvunKKgzf4SMZimVMET6HuzAyfGJS4ZMShUz94KLUdR': 1, 'HKPk4JUeJqcwEL2cyWG1U3fs8u5HPCVyffiK77prkRAB': 1, 'HubbLeXBb7qyLHt3x7gvYaRrxQmmgExb7fCJgDqFuB6T': 1, 'MKPzXmkHuFh2JEqkPV3vRvLSxWh79TL1Fw68Sc5RdQg': 1, 'MSTKTNxDrVTd32qF8kyaiUhFidmgPaYGU932FbRa7eK': 1, 'PapeRukGwkhaMRQcoZFPAdykRNaWPb7VsExKGqRCpfv': 1, 'RAFFLv4sQoBPqLLqQvSHLRSFNnnoNekAbXfSegbQygF': 1, 'SLMd1WANjRojqPvQwRUkcZLZQXioo6DrMohUB3SASvw': 1, 'STKRWxT4irmTthSJydggspWmkc3ovYHx62DHLPVv1f1': 1, 'STkwf3sbMapjy7KV3hgrJtcVvY4SvRxWQ8pj4Enw1i5': 1, 'TB1Dqt8JeKQh7RLDzfYDJsq8KS4fS2yt87avRjyRxMv': 1, 'TBCwReYDDw8SvwVVKJHgatzeXKrLHnaTPyDGwkUoBsq': 1, 'TWAPrdhADy2aTKN5iFZtNnkQYXERD9NvKjPFVPMSCNN': 1, 'VALY1TfX9RfPwNoVSfch8RUmgq5eNtWAjx4CVmDeYMo': 1, 'XdUP5LdgKezAX57J5wLbmNTbXHtHGQ9hQMwWJAFVZo1': 1, 'abcsvVSGQZxDKR1gw6cDqvTdHTj8YGWy73LyzJAesvT': 1, 'dp2waEWSBy5yKmq65ergoU3G6qRLmqa6K7We4rZSKph': 1, 'printvMS8ifuKbNugQwF4tf7DTXc5f3eKrTqWxgT8Vq': 1, 'qntmGodpGkrM42mN68VCZHXnKqDCT8rdY23wFcXCLPd': 1, 'stk17KkSJ7amyTVpGBHgo3Kcz52GjkzKYXuDwsFSk95': 1, 'stk8xj8cygGKnFoLE1GL8vHABcHUbYrnPCkxdL5Pr2q': 1, 'treaf4wWBBty3fHdyBpo35Mz84M8k3heKXmjmi9vFt5': 1, 'vsr2nfGVNHmSY8uxoBGqq8AQbwz3JwaEaHqGbsTPXqQ': 1, 'xAChdqv7tCSiU2gPTo41o9n3hnDLwtqhbK4zFTqJtE6': 1}
    insufficient = dict(sorted(insufficient.items(), key=lambda item: item[1], reverse=True))
    top_total += cal(error_count = insufficient, top2_program = ['675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8', '6Q4Xu2sXxMLMhS2pSBJwhDrL5AMWGbrBT3yaN48kYX7G'])
    print('='*16)

    invalid_status = {'675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8': 16524003, '9uW2TqLyfYyrcNVrgCy4jPpqDKQoBZhXWypzzFxbixQE': 503010, '3Bm3HukBbB1eREqrsS76wKBYB7MkCUznLrcevVoHzaqw': 58329, '8WhA6rGrFUj5JreBCBkgtkeKdiNR1BYKpwpPJwDoLP4B': 25763, '51ZBxXZrwTNmi2UdgHF1Q3anfmudopFHNKiUhVjiWrLF': 23733, 'BURSTBqFQnPSTSNno3X3Stdx91yCS51J9MH7uCP1knEX': 11791, '3HJDg13GwvQPdrYQY21zougWty6f1X8tNouRrCDWrzKy': 10056, 'routeUGWgWzqBWFcrCfv8tritsqukccJPu3q5GPP3xS': 5555, 'CcrAd4QH71GHcC5wBRkSsMUBjrMbqaGXULm5azpRMycb': 1167, '9y7vKvCd1P3N7R2g77rFoSVrLSvLAUCyPi4vMpXiuwnD': 898, '4QABZet2bwGvajeRYPfBQtHyaRVZ12oTHvrsabZ213qC': 846, 'Heg9dzyBM3BL8rkVcHrhfNoRm7RPn4wn3dCzhgfCfhYK': 798, 'Hq1x133jLiHYU45kN58tC8UUcDQ3rzDtUSNZkYKUk3ZR': 790, 'E23vtNG2mhHZFWzCx73zYey8mzfsUm5HBWQ9oS9vUYkw': 768, '8QxkA3bwq8Q3pL89S37iyrkv6VWjndzFAaRnVKjinXJN': 485, '4bfLZc1xx3NjpUV6vPWzsY6m8mz42rVVctTZ1CMd6WmJ': 188, 'GZUZRLKRz4tMJnq6sgtSioHonhXQKDqdE5BMJKP1mV5z': 185, 'EN1GMAXbcQF3ucku4wpxE45CKUaoBD3yiutrFqNfLfK7': 177, '3JmzqBoDLvNTPapBGCN7x23kTE5o7zkQ2fQhuyU3j9x6': 50, '9HMC8WNeLUJi1UckuAFsgZqJ55KXivE7L6Q1A2vrEofB': 11}
    invalid_status = dict(sorted(invalid_status.items(), key=lambda item: item[1], reverse=True))
    top_total += cal(error_count = invalid_status, top2_program = ['675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8', '9uW2TqLyfYyrcNVrgCy4jPpqDKQoBZhXWypzzFxbixQE'])
    print('='*16)

    delay = {'8BR3zs8zSXetpnDjCtHWnkpSkNSydWb3PTTDuVKku2uu': 10021216}
    print(f"total transactions: {10021216} {10021216/806468469}")
    top_total += 10021216
    print('='*16)

    invalid_input = {'675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8': 6888566, '9uW2TqLyfYyrcNVrgCy4jPpqDKQoBZhXWypzzFxbixQE': 578088, '8WhA6rGrFUj5JreBCBkgtkeKdiNR1BYKpwpPJwDoLP4B': 10615, 'JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB': 8810, '3Bm3HukBbB1eREqrsS76wKBYB7MkCUznLrcevVoHzaqw': 6295, 'JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4': 3963, 'DvYekppGNjU9Euvn8ts4fmmnDt3p9J7yQmpmCmzawY2W': 3530, 'GZUZRLKRz4tMJnq6sgtSioHonhXQKDqdE5BMJKP1mV5z': 2020, 'Go3rkvETdfWMwTgZsZVKXWF4MCdMNuQtym17q5Ap4WbN': 1570, 'routeUGWgWzqBWFcrCfv8tritsqukccJPu3q5GPP3xS': 1399, 'BURSTBqFQnPSTSNno3X3Stdx91yCS51J9MH7uCP1knEX': 290, '6Mys68BKcny4T7U1R1AMr8iVuGrDtMKiPgVbpGWCbbK5': 275, '2KehYt3KsEQR53jYcxjbQp2d2kCp4AkuQW68atufRwSr': 239, 'Evo1ve6p41CUZSdh7WCofrStMdhzUKAVcjWDNhet9Nkp': 175, '4bfLZc1xx3NjpUV6vPWzsY6m8mz42rVVctTZ1CMd6WmJ': 150, 'QoHLzip97BmPmkac7eXaVS2oiS6HizQ1bU3yD2FLEvD': 144, '3J3HFc8jXxdvZQ73PeUPJmPdM2EKpKonzBaYACCXzqkv': 130, '9MqJgoVX4rEQHv1RL2qJ2UWJRyapbsKoayhtUHrVG8hk': 68, '7PWnthtTsGnSpR4JLENYVoCJ5y5XwgELVbqgp6TkAFaH': 63, 'CcrAd4QH71GHcC5wBRkSsMUBjrMbqaGXULm5azpRMycb': 63, 'Heg9dzyBM3BL8rkVcHrhfNoRm7RPn4wn3dCzhgfCfhYK': 40, '4QABZet2bwGvajeRYPfBQtHyaRVZ12oTHvrsabZ213qC': 36, 'E23vtNG2mhHZFWzCx73zYey8mzfsUm5HBWQ9oS9vUYkw': 34, 'Hq1x133jLiHYU45kN58tC8UUcDQ3rzDtUSNZkYKUk3ZR': 33, '51ZBxXZrwTNmi2UdgHF1Q3anfmudopFHNKiUhVjiWrLF': 30, '9y7vKvCd1P3N7R2g77rFoSVrLSvLAUCyPi4vMpXiuwnD': 30, 'AzHrwdCsEZotAjr7sjenHrHpf1ZKYoGBP6N7HVhEsyen': 25, 'CountdownKPVHPBk5si8rg5nyZwdjZPWBtYD5rEtHqCd': 20, '9JcNgNMPGSbjLhuXtoVd6e81n1g1r1ZXUon2gzF5XSyr': 16, '3HJDg13GwvQPdrYQY21zougWty6f1X8tNouRrCDWrzKy': 13, 'AJHY33LqE2dWstq2k7uPDtCAz7mDUXBX3CfL4iazgvfw': 13, '36z9tipgENz4wgt2XxnxXZVYQMtDPNw5UXeucYcH9dXv': 9, 'BSxRXGGfeB6ShDzosRjKjsXmgcNhDzxcgEB4Pxgt9TDi': 7, 'GzxwDvhbNcKTt4LBez3k9CuKZfuq5N3mZKYkBTKn1nKX': 5, 'JUP2jxvXaqu7NQY1GmNF4m1vodw12LVXYxbFL2uJvfo': 5, '44vxtqq7hx2UTcogDU4mraoPD2775QMUza4oBg29p9BX': 4, '8888882FsxBq7dmc4N1zcMWSKbbsuKgXvfUif2P7S6K6': 4, '2nAAsYdXF3eTQzaeUQS3fr4o782dDg8L28mX39Wr5j8N': 3, '3qCUc2TGsHFw4o31hsYjWCDS5Wsci8pBKLfuMBZznTrJ': 1, 'DS2Sj6NtroGYs2Qgda299j8U1gYu1LosZByKHor1pr3s': 1, 'GwbwsDGDzpjYFiFfhqLUiNN6j1NP5bb5jdqW7gK9ASpr': 1, 'Hye5Ahzqv9fY8LsjygfXCmkuVL67rgKRNzqZSEhpwXUf': 1}
    invalid_input = dict(sorted(invalid_input.items(), key=lambda item: item[1], reverse=True))
    top_total += cal(error_count = invalid_input, top2_program = ['675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8', '9uW2TqLyfYyrcNVrgCy4jPpqDKQoBZhXWypzzFxbixQE'])
    print('='*16)

    print(f"other transactions: {806468469-top_total} {(806468469-top_total)/806468469}")

if __name__ == "__main__":
    start_time = time.time()
    # signers = get_signer_cnt_from_db()
    # plot_signer_pie(signers)
    # get_failed_error_log_from_db()
    post_handle(get_failed_error_log_cnt_from_db())
    # cals()
    # results = get_failed_ratio_per_hour_from_db()
    # plot_tx_cnt_per_hour(results)
    end_time = time.time()
    print(f"Run Time:{end_time-start_time}")
