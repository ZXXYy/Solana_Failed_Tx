import os
import time
import logging
import requests

import pandas as pd
import numpy as np

from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

logger = logging.getLogger(__name__)
load_dotenv()
RPC_URL = os.getenv("RPC_URL")
DEBUG = True if os.getenv("DEBUG") == "True" else False

def sample_days_from_weeks():
    logger.info("Start sampling blocks from weeks")
    # 设置起止日期
    start_date = datetime(2023, 8, 1)
    end_date = datetime(2024, 7, 31)

    # 生成日期范围
    date_range = pd.date_range(start=start_date, end=end_date)

    # 转换为DataFrame并添加周数和星期几
    df = pd.DataFrame({'date': date_range})
    df['week'] = df['date'].dt.isocalendar().week
    df['year'] = df['date'].dt.isocalendar().year
    df['weekday'] = df['date'].dt.strftime('%A')

    # 为跨年的周数做调整
    df['week'] = df.apply(lambda x: x['week'] + 52 if x['year'] == 2024 else x['week'], axis=1)

    sampled_dates = pd.DataFrame()
    target_per_weekday = len(df['week'].unique()) // 7  # 每个星期应该有的样本数

    # 按周循环采样
    for week in df['week'].unique():
        week_data = df[df['week'] == week]
        
        # 检查当前已采样的每个星期的数量
        if len(sampled_dates) > 0:
            current_counts = sampled_dates['weekday'].value_counts()
            # 找出采样数量较少的星期
            if len(current_counts) < 7:
                # 如果某些星期还没有样本，优先选择这些星期
                missing_weekdays = set(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 
                                      'Friday', 'Saturday', 'Sunday']) - set(current_counts.index)
                if missing_weekdays:
                    available_days = week_data[week_data['weekday'].isin(missing_weekdays)]
                    if not available_days.empty:
                        sampled_day = available_days.sample(n=1)
                        sampled_dates = pd.concat([sampled_dates, sampled_day])
                        continue
            
            # 选择数量最少的星期
            undersampled = current_counts[current_counts < target_per_weekday].index
            if len(undersampled) > 0:
                available_days = week_data[week_data['weekday'].isin(undersampled)]
                if not available_days.empty:
                    sampled_day = available_days.sample(n=1)
                    sampled_dates = pd.concat([sampled_dates, sampled_day])
                    continue

        # 如果没有特殊条件，随机选择
        sampled_day = week_data.sample(n=1)
        sampled_dates = pd.concat([sampled_dates, sampled_day])

    # 按日期排序
    sampled_dates = sampled_dates.sort_values('date')
    
    # write sampled dates to file
    sampled_dates.to_csv("data/sampled_dates.csv", index=False)

    return sampled_dates


def timestamp_to_datetime(timestamp: int):
    return datetime.fromtimestamp(timestamp,tz=timezone.utc)

def get_block_time(block_id: int, retries: int = 5):  
    if RPC_URL is None:
        logger.error("Please provide your RPC endpoint!")
        return
    headers = {"Content-Type": "application/json"}
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getBlockTime",
        "params": [block_id]
    }
    for attempt in range(retries):
        try:
            response = requests.post(RPC_URL, headers=headers, json=payload)
            response.raise_for_status()  # Raise an error for bad responses
            if response.json().get('result'):
                return response.json()['result']
            return None
        except requests.exceptions.SSLError as ssl_err:
            logger.error(f"SSL error occurred: {ssl_err}. Attempt {attempt + 1} of {retries}.")
        except requests.exceptions.RequestException as req_err:
            logger.error(f"Request error occurred: {req_err}. Attempt {attempt + 1} of {retries}.")
        
        time.sleep(1+attempt*2)  # Wait before retrying

# binary search to find the block id
def datetime_to_block_id(target_date: datetime, left_block_id: int, right_block_id: int):
    target_timestamp = int(target_date.timestamp())
    logger.info(f"targt_date: {target_date.strftime('%Y-%m-%d %H:%M:%S')}")
    target_block_id = None
    left, right = left_block_id, right_block_id
    closest_time_diff = 60 # 60 seconds
    cnt = 0
    while left <= right:
        cnt += 1
        logger.info(f"left: {left}, right: {right}, cnt: {cnt}")
        mid = (left + right) // 2
        block_time = get_block_time(mid)

        if block_time is None:
            left = left + 10 # 如果获取不到blocktime，可能是skipped slot，尝试下一个
            time.sleep(1)
            continue

        logger.debug(f"block_time: {timestamp_to_datetime(block_time).strftime('%Y-%m-%d')} ")
        time_diff = abs(block_time - target_timestamp)
        logger.debug(f"block_time: {block_time}, target_time: {target_timestamp}, time_diff: {time_diff}") 
        
        if time_diff < closest_time_diff:
            target_block_id = mid
            break

        if block_time < target_timestamp:
            left = mid + 1
        else:
            right = mid - 1

        time.sleep(1)
    return target_block_id


if __name__ == "__main__":
    # get sample dates
    if not os.path.exists("data/sampled_dates.csv"):
        sampled_dates = sample_days_from_weeks()
    elif os.path.exists("data/sampled_dates_with_block_id.csv"):
        sampled_dates = pd.read_csv("data/sampled_dates_with_block_id.csv")
    else:
        sampled_dates = pd.read_csv("data/sampled_dates.csv")
        sampled_dates['start_block_id'] = 0
        sampled_dates['end_block_id'] = 0

    # get sample block ranges
    START_BLOCK = 208703000 # 2023-08-01
    END_BLOCK = 280826900   # 2024-07-31
    start_block_ids, end_block_ids = [], []
    for i, row in sampled_dates.iterrows():
        date = row['date']
        if row['start_block_id'] > 0:
            start_block_ids.append(row['start_block_id'])
            end_block_ids.append(row['end_block_id'])
            logger.info(f"already get {date}: {row['start_block_id']}-{row['end_block_id']}")
            continue

        if type(date) == str:
            date = datetime.strptime(date, '%Y-%m-%d')
        date = date.replace(tzinfo=timezone.utc)

        logger.info(f"start searching for {date.strftime('%Y-%m-%d %H:%M:%S')}")
        
        start_time = time.time()
        start_block_id = datetime_to_block_id(date, START_BLOCK, END_BLOCK) 
        start_block_id = START_BLOCK if start_block_id is None else start_block_id
        end_block_id = datetime_to_block_id(date+timedelta(days=1)-timedelta(seconds=1), start_block_id, END_BLOCK)

        logger.info(f"end searching for {date.strftime('%Y-%m-%d %H:%M:%S')}, cost {time.time()-start_time} seconds")
        logger.info(f"{date.strftime('%Y-%m-%d %H:%M:%S')}: {start_block_id}-{end_block_id}")
        
        # write start and end block id to file
        sampled_dates.at[i, 'start_block_id'] = start_block_id
        sampled_dates.at[i, 'end_block_id'] = end_block_id
        sampled_dates.to_csv("data/sampled_dates_with_block_id2.csv", index=False)

    sampled_dates.to_csv("data/sampled_dates_with_block_id.csv", index=False)
    