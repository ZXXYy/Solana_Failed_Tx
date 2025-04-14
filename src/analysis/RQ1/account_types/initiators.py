import sys
import os
import time
import pymongo
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utils.utils import deprecated, timer

@deprecated
def get_failed_txs_for_bot_or_human():
    myclient = pymongo.MongoClient("mongodb://localhost:27018/")
    mydb = myclient["solana"]
    signer_labels = mydb["signer_labels_one_year"]
    pipeline = [
        {
            "$lookup": {
                "from": "signer_cnt",
                "localField": "signer",
                "foreignField": "_id",
                "as": "signer_cnt"
            }
        },
        {
            "$unwind": "$signer_cnt"
        },
        {
            "$project": {
                "_id": 0,
                "label": 1,
                "signer": 1,
                "failed_count": "$signer_cnt.failed_count",
                "success_count": "$signer_cnt.success_count",

            }
        }, 
        {
            "$group": {
                "_id": "$label",
                "failed_count": {
                    "$sum": "$failed_count"
                },
                "success_count": {
                    "$sum": "$success_count"
                },
                "count": {
                    "$sum": 1
                }
            }
        }
    ]
    results = signer_labels.aggregate(pipeline)
    for result in results:
        print(result)

def get_top_failed_signers(is_bot):
    myclient = pymongo.MongoClient("mongodb://localhost:27018/")
    mydb = myclient["solana"]
    signer_labels = mydb["signer_labels_one_year_decision_tree"]
    pipeline = [
        {
            "$lookup": {
                "from": "signer_cnt",
                "localField": "signer",
                "foreignField": "_id",
                "as": "signer_cnt"
            }
        },
        {
            "$unwind": "$signer_cnt"
        },
        {
            "$project": {
                "_id": 0,
                "label": 1,
                "signer": 1,
                "failed_count": "$signer_cnt.failed_count",
                "success_count": "$signer_cnt.success_count",
                "failed_ratio": "$signer_cnt.failed_ratio"
            }
        }, 
        {
            '$match': {
                "label": 1 if is_bot else 0
            },
        },
        {
            "$sort": {
                "failed_count": -1,
                "failed_ratio": -1,
            }
        },
        
    ]
    results = signer_labels.aggregate(pipeline)
    failed_count = []
    success_count = []
    top_10_failure_account = []
    i = 0
    for result in results:
        failed_count.append(result['failed_count'])
        success_count.append(result['success_count'])
        if i < 10:
            print(result)
            top_10_failure_account.append(result)
        i += 1

    print(f"Total failed: {sum(failed_count)}")
    print(f"Total success: {sum(success_count)}")
    print(f"failed_ratio: {sum(failed_count) / sum(success_count)}")
    print(f"Total signers: {i}")

    return failed_count, success_count, top_10_failure_account

if __name__ == "__main__":
    # get_failed_txs_for_bot_or_human()
    with timer("Bot Signer Calculation"):
        bot_failed, bot_success, _ = get_top_failed_signers(is_bot=True)
        # plot_failed_cdf(bot_failed, bot_success, is_bot=True)
   
    with timer("Human Signer Calculation"):
        human_failed, human_success, _ = get_top_failed_signers(is_bot=False)
        # plot_failed_cdf(human_failed, human_success, is_bot=False)

