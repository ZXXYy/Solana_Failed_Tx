import os
import re
import json
import time
import asyncio
import aiohttp

import logging
import pandas as pd
import numpy as np

from tqdm import tqdm
from dotenv import load_dotenv
from collections import defaultdict
from datetime import datetime, timedelta

from buildDataset import insert_txs_per_block

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

logger = logging.getLogger(__name__)
load_dotenv()
RPC_URL = os.getenv("RPC_URL")
DEBUG = True if os.getenv("DEBUG") == "True" else False

# Semaphore to limit concurrency (e.g., max 100 tasks at a time)
semaphore = asyncio.Semaphore(100)

def process_log_message(tx):
    if tx["meta"]['err'] is None:
        return None
    log_messages = tx['meta']['logMessages']
    failed_log = ""
    for log in reversed(log_messages):
        failed_log = log + '\n' + failed_log
        if 'success' in log:
            break
    return failed_log
    

def process_failed_inst(tx):
    if tx["meta"]['err'] is None:
        return None
    failed_idx = tx['meta']['err']
    if "InstructionError" in failed_idx:
        failed_inst = tx['transaction']['message']['instructions'][failed_idx['InstructionError'][0]]
        failed_program = tx['transaction']['message']['accountKeys'][failed_inst['programIdIndex']]
        failed_inst_data = failed_inst["data"]
        failed_inst_accounts = []
        accountKeys = tx['transaction']['message']['accountKeys'] + tx['meta']['loadedAddresses']['writable'] + tx['meta']['loadedAddresses']['readonly']
        for account in failed_inst["accounts"]:
            failed_inst_accounts.append(accountKeys[account])
        return {
            'program': failed_program,
            'accounts': failed_inst_accounts,
            'data': failed_inst_data
        }
    return None

def process_success_insts(tx):
    if tx["meta"]['err'] is not None:
        return None
    insts = tx['transaction']['message']['instructions']
    accounts = tx['transaction']['message']['accountKeys'] + tx['meta']['loadedAddresses']['writable'] + tx['meta']['loadedAddresses']['readonly']
    return {
        'accounts': accounts,
        'instructions': insts
    }

def process_token_balance(tx):
    token_balance = defaultdict(dict)
    signer_sol_post_balance = tx['meta']['postBalances'][0]
    signer_sol_pre_balance  = tx['meta']['preBalances'][0]
    token_balance["sol"]['pre_balance'] = signer_sol_pre_balance
    token_balance["sol"]['post_balance'] = signer_sol_post_balance
    signer = tx['transaction']['message']['accountKeys'][0]
    for pre_token_balance in tx['meta']['preTokenBalances']:
        if pre_token_balance['accountIndex'] == 0 or pre_token_balance['owner'] == signer:
            token_balance[pre_token_balance['mint']]['pre_balance'] = pre_token_balance['uiTokenAmount']
    for post_token_balance in tx['meta']['postTokenBalances']:
        if post_token_balance['accountIndex'] == 0 or post_token_balance['owner'] == signer:
            token_balance[post_token_balance['mint']]['post_balance'] = post_token_balance['uiTokenAmount']
    return token_balance


def process_is_vote(tx):
    if 'Vote111111111111111111111111111111111111111' in tx['transaction']['message']['accountKeys']:
        return True
    return False

    
def handle_txs(blk):
    if 'result' not in blk:
        return []
    txs = blk["result"]["transactions"]
    processed_txs = []
    
    for tx in txs:
        is_vote = process_is_vote(tx)
        if is_vote:
            processed_txs.append(
                {   
                    "vote": True,
                    "success": True if tx['meta']['err'] is None else False                
                }
            )
            continue
        processed_txs.append(
            {
                "computeUnitsConsumed": tx["meta"]["computeUnitsConsumed"],
                "error": tx["meta"]["err"],
                "fee": tx["meta"]["fee"],
                "failedLogMessages": process_log_message(tx),
                "failedInstruction": process_failed_inst(tx),
                "successInstructions": process_success_insts(tx),
                "tokenBalance": process_token_balance(tx),
                "blockTime": blk["result"]["blockTime"],
                "transactionHash": tx["transaction"]["signatures"][0],
                "signer": tx['transaction']['message']['accountKeys'][0]
            }
        )
    return processed_txs

async def handle_rate_limit(response, retry_count):
    retry_after = response.headers.get('Retry-After')
    if retry_after:
        try:
            # Check if Retry-After is in seconds
            wait_time = int(retry_after)
        except ValueError:
            # If not in seconds, parse Retry-After as HTTP-date
            retry_date = time.mktime(time.strptime(retry_after, '%a, %d %b %Y %H:%M:%S GMT'))
            wait_time = retry_date - time.time()
        wait_time = max(0, wait_time)
        logger.warning(f"Rate limit hit, retrying in {wait_time} seconds...")
        await asyncio.sleep(wait_time)
    else:
        # Default backoff strategy if Retry-After is missing
        sleep_time = 60 * retry_count  # Linear backoff
        # logger.warning(f"No Retry-After header, defaulting to {sleep_time} seconds...")
        await asyncio.sleep(sleep_time)


async def crawl_block(block_id):
    if RPC_URL is None:
        logger.error("Please provide your RPC endpoint!")
        return
    # if is_crawled(block_id):
    #     return 
    retry_count = 0
    retry_limit = 5
    while retry_count < retry_limit:
        async with aiohttp.ClientSession() as session:
            try:
                url = RPC_URL
                headers = {"Content-Type": "application/json"}
                data = {
                    "jsonrpc": "2.0",
                    "id":1,
                    "method":"getBlock",
                    "params": [
                    block_id,
                    {
                        "maxSupportedTransactionVersion": 0,
                        "encoding": "json",
                        "transactionDetails":"full",
                        "rewards": True
                    }
                    ]
                }
                async with session.post(url, json=data, headers=headers) as response:
                    result =  await response.json()
                    if response.status == 429:
                        await handle_rate_limit(response, retry_count)
                    else:
                        txs = handle_txs(result)
                        if block_id % 1000 == 0:
                            print(f"{block_id}--{len(txs)}")
                        else:
                            print(block_id)
                        if len(txs)>0:
                            # await async_write_to_file(block_id, txs)
                            await insert_txs_per_block(block_id, txs)
                        return None
            except aiohttp.ClientError as e:
                logger.warning("SSL or Connection Error, retrying...")
                print(f"Request failed: {e}")
                retry_count += 1
                await asyncio.sleep(60 * retry_count)
            except Exception as e:
                logger.error(f"An error occurred: {e}")
                retry_count += 1
                await asyncio.sleep(60 * retry_count)
        
# Wrapper function to enforce the concurrency limit
async def limited_crawl_block(block):
    async with semaphore:
        await crawl_block(block)


async def crawl_blocks(start_block, end_block):
    tasks = []
    # 252345000 March 06, 2024 00:04:24
    # 253566000 March 11, 2024 19:29:27 +UTC
    # 255643000 March 21, 2024 23:55:21 +UTC
    # 264100000 May 05, 2024 23:57:04
    # 281800000 August 05, 2024 23:59:49 
    blocks =   range(252345000, 252350000) if DEBUG else range(start_block, end_block) # for alchemy
    # blocks =  range(253566000, 253566005)if DEBUG else range(253566000, 253966000) # for insantnode

    tasks = [asyncio.create_task(limited_crawl_block(i)) for i in blocks]
    await asyncio.gather(*tasks)

async def main():
    sampled_dates = pd.read_csv("data/sampled_dates_with_block_id.csv")
    if 'is_crawled' not in sampled_dates.columns:
        sampled_dates['is_crawled'] = False

    for i, row in sampled_dates.iterrows():
        if row['is_crawled']:
            continue
        start_block_id = row['start_block_id']
        end_block_id = row['end_block_id']

        logger.info(f"start crawling {start_block_id}-{end_block_id}")
        await (crawl_blocks(start_block_id, end_block_id))
        sampled_dates.at[i, 'is_crawled'] = True
        sampled_dates.to_csv("data/sampled_dates_with_block_id2.csv", index=False)
        logger.info(f"crawling {start_block_id}-{end_block_id} finished")
    
    sampled_dates.to_csv("data/sampled_dates_with_block_id.csv", index=False)

if __name__ == "__main__":
    start_time = time.time()
    asyncio.run(main())
    end_time = time.time()
    logger.info(f"Run Time:{end_time-start_time}")
