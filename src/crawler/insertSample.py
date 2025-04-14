import os
import json
import pymongo
from pymongo.errors import BulkWriteError
from dotenv import load_dotenv

load_dotenv()
DB_CLIENT = os.getenv("DB_CLIENT")

def sample_transactions():
    myclient = pymongo.MongoClient(DB_CLIENT)
    mydb = myclient["solana"]
    txs_table = mydb["txs"]
    pipeline = [
        {
            "$match": { "$expr": { "$eq": [ { "$type": "$vote" }, "missing" ] } },  # select non-vote transactions
        },
        {
            "$project": {
                "_id": 0,
            }
        },
        {
            "$limit": 10000 
        }
    ]
    results = list(txs_table.aggregate(pipeline, allowDiskUse=True))
    print(f"Number of sample transactions: {len(results)}")
    # write results to json file
    with open("data/sample_transactions.json", "w") as f:
        json.dump(results, f, indent=4)

def write_sample_transactions_to_db():
    sample_txs = json.load(open("data/sample_transactions.json"))
    myclient = pymongo.MongoClient(DB_CLIENT)
    mydb = myclient["solana"]
    txs_table = mydb["sample_txs"]
    txs_table.create_index([("block_id", 1), ("rank", 1)], unique=True)
    try:
        if len(sample_txs) > 0:
            x = txs_table.insert_many(sample_txs)
    except BulkWriteError as e:
        for err in e.details['writeErrors']:
            print(f"Error: {err['errmsg']} (on document with _id: {err['op']['_id']})")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # sample_transactions()
    write_sample_transactions_to_db()