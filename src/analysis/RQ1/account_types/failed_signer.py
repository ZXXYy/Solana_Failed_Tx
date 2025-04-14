import pymongo
import time

import matplotlib.pyplot as plt


def get_signer_cnt_from_db():
    myclient = pymongo.MongoClient("mongodb://localhost:27018/")
    mydb = myclient["solana"]
    txs_table = mydb["txs_one_year"]
    # txs_table.create_index([("block_id", 1)], unique=True)
    # txs_table.create_index([("signer", 1)])
    pipeline = [
        {
            "$match": {
                "$and": [
                        { "$expr": { "$eq": [ { "$type": "$vote" }, "missing" ] } },  # 检查 vote 字段是否不存在
                        { "$expr": { "$ne": [ { "$type": "$signer" }, "missing" ] } },  # 检查 signer字段存在
                        # { "block_id": { "$gte": 255117800, "$lte": 255643000 } }
                    ]
            }
        },
        {
            "$group": {
                "_id": "$signer",
                "total_count": {
                    "$sum": 1
                },
                "failed_count": {
                    "$sum": {
                        "$cond": [ { "$eq": [ "$error", None ] }, 0, 1 ]
                    }
                },
                "success_count": {
                    "$sum": {
                        "$cond": [ { "$eq": [ "$error", None ] }, 1, 0 ]
                    }
                }
            }
        },
        {
            "$project": {
                "_id": 1,
                "total_count": 1,
                "failed_count": 1,
                "success_count": 1,
            }
        },
        {
            "$out": "signer_cnt"
        }
    ]
    results = txs_table.aggregate(pipeline)
    
# def get_signer_cnt_from_db():
#     myclient = pymongo.MongoClient("mongodb://localhost:27017/")
#     mydb = myclient["solana"]
#     signers = mydb["failed_signer_cnt"]
#     results = signers.find()
#     return list(results)

if __name__ == "__main__":
    start_time = time.time()
    # signers = get_signer_cnt_from_db()
    # plot_signer_pie(signers)
    get_signer_cnt_from_db()
    # results = get_failed_ratio_per_hour_from_db()
    # plot_tx_cnt_per_hour(results)
    end_time = time.time()
    print(f"Run Time:{end_time-start_time}")