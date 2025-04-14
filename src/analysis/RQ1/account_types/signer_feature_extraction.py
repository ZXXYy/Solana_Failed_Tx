import os
import sys
import time
import logging
import pymongo
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from tqdm import tqdm
from itertools import pairwise
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import MinMaxScaler

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utils.utils import get_db_client, timer, db_table_exists, setup_logger

DB_TABLE_SIGNER_RAW_FEATURES = "sign_raw_features"
DB_TABLE_SIGNER_FEATURES = "signer_features_one_year_v2"

def get_signer_raw_feature(txs_table, args):
    # drop sign_raw_features_one_year
    if DB_TABLE_SIGNER_RAW_FEATURES in mydb.list_collection_names():
        mydb[DB_TABLE_SIGNER_RAW_FEATURES].drop()
    
    # read sampled dates
    if args.debug:
        start_block_ids = [209292602]
        end_block_ids = [209294602]
    else:
        sampled_dates = pd.read_csv("data/sampled_dates_with_block_id.csv")
        start_block_ids = list(sampled_dates['start_block_id'])
        end_block_ids = list(sampled_dates['end_block_id'])
    
    for start_block_id, end_block_id in zip(start_block_ids, end_block_ids):
        with timer(f"Processing {start_block_id}-{end_block_id}", logger=logger, level=logging.INFO):
            pipeline = [
                {
                    "$match": {
                        "block_id": { "$gte": start_block_id, "$lte": end_block_id }
                    }
                },
                {
                        "$project": {
                        "blockTime": 1,
                        # "computeUnitsConsumed": 1,
                        "error": 1,
                        "signer": 1,
                    }
                },
                {
                    "$group": {
                        "_id": {
                            "signer": "$signer",
                            "blockTime": "$blockTime",
                        },
                        "total_count": {
                            "$sum": 1
                        },
                        "failed_count": {
                            "$sum": {
                                "$cond": [ { "$ne": [ "$error", None ] }, 1, 0 ]
                            }
                        },
                        # "consumed_units": {
                        #     "$push": "$computeUnitsConsumed"
                        # },
                    }
                },
                {
                    "$merge": {  # 替换$out，使用$merge
                        "into": DB_TABLE_SIGNER_RAW_FEATURES,
                        "whenMatched": [
                            {
                                "$addFields": {
                                    "total_count": {
                                        "$add": ["$total_count", "$$new.total_count"]
                                    },
                                    "failed_count": {
                                        "$add": ["$failed_count", "$$new.failed_count"]
                                    }
                                }
                            }
                        ],
                        "whenNotMatched": "insert"
                    }
                },
                # {
                #     "$sort": {
                #         "_id.signer": 1,
                #         "_id.blockTime": 1,
                #     }
                # },
                # { "$out": "sign_raw_features"}
            ]
            results = txs_table.aggregate(pipeline, allowDiskUse=True)

def get_signer_feature(signer, table_signer_raw_features, table_signer_features, args):
    # get raw features for signer
    pipeline = [
        {
            "$match": {
                 "_id.signer": signer ,
            }
        },
        {
            "$project":{
                "_id.blockTime": 1,
                "total_count": 1,
                "failed_count": 1,
            }
        }
    ]
    results = table_signer_raw_features.aggregate(pipeline, allowDiskUse=True)

    # extract features for signer
    try:
        results = list(results)
        valid_results = [r for r in results if 'blockTime' in r['_id']]
        block_times = [r['_id']['blockTime'] for r in valid_results]
        start_time, end_time = block_times[0], block_times[-1]
        interval = [t2 - t1 for t1, t2 in pairwise(block_times)] 
        max_interval = max(interval) if interval else 0
        # filter interval < 60*60*12 (12 hours)
        interval_12h = [i for i in interval if i < 60*60*12]
        interval_24h = [i for i in interval if i < 60*60*24]
        total_block_txs = sum(r["total_count"] for r in valid_results)
        total_failed_txs = sum(r["failed_count"] for r in valid_results)
        total_result_len = len(valid_results)
        if args.debug:
            print("Txs per block", total_block_txs/total_result_len)
            print("Failed Txs per block", total_failed_txs/total_result_len)
            print("Total blocks", total_result_len)
            print("Interval variance", np.var(interval) if len(interval) > 0 else 0)
            print("Mean interval", sum(interval)/len(interval) if len(interval) > 0 else 0)
            print("Interval 12h variance", np.var(interval_12h) if len(interval_12h) > 0 else 0)
            print("Mean interval 12h", sum(interval_12h)/len(interval_12h) if len(interval_12h) > 0 else 0)
            print("Interval 24h variance", np.var(interval_24h) if len(interval_24h) > 0 else 0)
            print("Mean interval 24h", sum(interval_24h)/len(interval_24h) if len(interval_24h) > 0 else 0)
            # print("CU variance", np.var(consumed_units))
            # print("Mean CU", sum(consumed_units)/len(consumed_units))
        res = {
            "signer": signer,
            "interval_variance": np.var(interval) if len(interval) > 0 else 0,
            "interval_mean": sum(interval)/len(interval) if len(interval) > 0 else 0,
            "interval_12h_variance": np.var(interval_12h) if len(interval_12h) > 0 else 0,
            "interval_12h_mean": sum(interval_12h)/len(interval_12h) if len(interval_12h) > 0 else 0,
            "interval_24h_variance": np.var(interval_24h) if len(interval_24h) > 0 else 0,
            "interval_24h_mean": sum(interval_24h)/len(interval_24h) if len(interval_24h) > 0 else 0,
            "max_interval": max_interval,
            # "cu_variance": np.var(consumed_units),
            # "cu_mean": sum(consumed_units)/len(consumed_units),
            "txs_per_block": total_block_txs/total_result_len,
            "failed_txs_per_block": total_failed_txs/total_result_len,
            "total_blocks": total_result_len,
            "total_txs": total_block_txs,
            "total_failed_txs": total_failed_txs,  
            "active_time": end_time-start_time
        }
    except Exception as e:
        logger.error(f"{signer}: Exception {e}")
        print(block_times)
        res = None

    table_signer_features.update_one({"signer": signer}, {"$set": res}, upsert=True)

def get_signers_from_db(signers):
    results = signers.aggregate([
            { "$group": { "_id": "$_id.signer" } },
            { "$sort": { "_id": 1 } },
            { "$project": { "_id": 1 } }
        ], allowDiskUse=True
    )
    return [result['_id'] for result in results]

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="debug mode")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    global logger
    logger = setup_logger(level=logging.DEBUG if args.debug else logging.INFO, name="signer_feature_extraction")
    myclient, mydb, txs_table = get_db_client()

    try:
        #  get signer raw features
        if not db_table_exists(mydb, DB_TABLE_SIGNER_RAW_FEATURES):
            with timer("get_signer_raw_feature", logger=logger, level=logging.INFO):
                get_signer_raw_feature(txs_table, args)
            with timer("create_index for sign_raw_features", logger=logger, level=logging.INFO):
                mydb[DB_TABLE_SIGNER_RAW_FEATURES].create_index([("_id.signer", 1)])
        else:
            logger.info(f"{DB_TABLE_SIGNER_RAW_FEATURES} already exists")
            
        # get all signers
        signers = get_signers_from_db(mydb[DB_TABLE_SIGNER_RAW_FEATURES])
        logger.info(f"Total signers: {len(signers)}")
        if args.debug:
            signers = signers[:10]
        
        # extract signer features
        signer_features = mydb[DB_TABLE_SIGNER_FEATURES]
        signer_features.create_index([("signer", 1)], unique=True)    
        for signer in tqdm(signers):
            try:
                with timer(f"get_signer_feature for {signer}", logger=logger, level=logging.DEBUG):
                    get_signer_feature(signer, mydb[DB_TABLE_SIGNER_RAW_FEATURES], mydb[DB_TABLE_SIGNER_FEATURES], args)
            except Exception as e:
                logger.error(f"{signer}: Exception {e}")        
    finally:
        myclient.close()
