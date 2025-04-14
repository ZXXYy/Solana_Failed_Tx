import os
import sys
import time
import asyncio
import pymongo
from pymongo.errors import BulkWriteError
import motor.motor_asyncio

from dotenv import load_dotenv

# sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
# from utils.fileOps import async_read_from_file

load_dotenv()
DB_CLIENT = os.getenv("DB_CLIENT")
START_BLOCK = 252345000
END_BLOCK = 252345005


semaphore = asyncio.Semaphore(100)
myclient = pymongo.MongoClient(DB_CLIENT)
# myclient = motor.motor_asyncio.AsyncIOMotorClient('mongodb://localhost:27017')
mydb = myclient["solana"]
txs_table = mydb["txs_one_year"]
txs_table.create_index([("block_id", 1), ("rank", 1)], unique=True)

async def insert_txs_per_block(blkid, txs=None):
    if txs is None:
        return
    for i, tx in enumerate(txs):
        tx['block_id'] = blkid
        tx['rank'] = i
    try:
        if len(txs) > 0:
            x = txs_table.insert_many(txs)
            # print(blkid)
    except BulkWriteError as e:
        for err in e.details['writeErrors']:
            print(f"Error: {err['errmsg']} (on document with _id: {err['op']['_id']})")
    except Exception as e:
        print(f"{blkid}: {e}")

        
async def delete_txs_per_block(blkid):
    if blkid % 1000 == 0:
        print(blkid)
    query = {
        'block_id': blkid
    }
    txs_table.delete_many(query)

# Wrapper function to enforce the concurrency limit
async def limited_insert_txs_per_block(block):
    async with semaphore:
        await insert_txs_per_block(block)

async def limited_delete_txs_per_block(blkid):
    async with semaphore:
        await delete_txs_per_block(blkid)

if __name__ == "__main__":
    print(mydb.list_collection_names())