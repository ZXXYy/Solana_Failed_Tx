import pandas as pd
import os
from dune_api import execute_dune_query, init_dune_client

# from dune website: https://dune.com/queries/4584719
# HOURLY_TX_QUERY_FOR_REF = """
# SELECT 
#     DATE_TRUNC('hour', time) as hour,
#     SUM(total_non_vote_transactions) as total_txs,
#     CAST(SUM(failed_non_vote_transactions) AS DOUBLE) / (SUM(failed_non_vote_transactions) + SUM(successful_non_vote_transactions)) as failed_ratio
# FROM solana.blocks 
# WHERE time >= CAST(DATE {{start_date}} AS TIMESTAMP) AND time < CAST(DATE {{start_date}} + INTERVAL '1' DAY AS TIMESTAMP)
# GROUP BY 1
# ORDER BY 1
# """
HOURLY_TX_QUERY_ID = 4584719


def time_trend(query_id, query_params) -> pd.DataFrame:
    dune = init_dune_client()
    query_result: pd.DataFrame = execute_dune_query(dune, query_id, query_params)
    return query_result

if __name__ == "__main__":
    date_dir = "/data0/xiaoyez/Solana_Ecosystem/data/"
    time_trend_dir = f"{date_dir}/time_trend/"
    if not os.path.exists(time_trend_dir):
            os.makedirs(time_trend_dir)
    
    df_sample = pd.read_csv(f"{date_dir}/sampled_dates_with_block_id.csv")
    dates = df_sample["date"].tolist()
    
    for date in dates:
        if os.path.exists(f"{time_trend_dir}/{date}.csv"):
            continue
        query_result = time_trend(HOURLY_TX_QUERY_ID, {"start_date": f"\'{date}\'"})
        query_result.to_csv(f"{time_trend_dir}/{date}.csv", index=False)
