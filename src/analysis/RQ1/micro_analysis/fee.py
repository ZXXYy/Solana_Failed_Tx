import os
import pandas as pd
from dune_api import execute_dune_query, init_dune_client
from dune_client.client import DuneClient

# https://dune.com/queries/4586782
FEE_QUERY_ID = 4586782
FEE_QUERY_FOR_REF = """
WITH dates AS (
    SELECT date FROM (VALUES 
        (CAST('2023-08-04' AS DATE)), (CAST('2023-08-09' AS DATE)), (CAST('2023-08-14' AS DATE)), 
        (CAST('2023-08-24' AS DATE)), (CAST('2023-09-03' AS DATE)), (CAST('2023-09-09' AS DATE)),
        (CAST('2023-09-12' AS DATE)), (CAST('2023-09-20' AS DATE)), (CAST('2023-09-28' AS DATE)),
        (CAST('2023-10-08' AS DATE)), (CAST('2023-10-10' AS DATE)), (CAST('2023-10-16' AS DATE)),
        (CAST('2023-10-26' AS DATE)), (CAST('2023-10-30' AS DATE)), (CAST('2023-11-09' AS DATE)),
        (CAST('2023-11-18' AS DATE)), (CAST('2023-11-20' AS DATE)), (CAST('2023-11-28' AS DATE)),
        (CAST('2023-12-08' AS DATE)), (CAST('2023-12-14' AS DATE)), (CAST('2023-12-20' AS DATE)),
        (CAST('2023-12-26' AS DATE)), (CAST('2024-01-07' AS DATE)), (CAST('2024-01-08' AS DATE)),
        (CAST('2024-01-17' AS DATE)), (CAST('2024-01-26' AS DATE)), (CAST('2024-02-03' AS DATE)),
        (CAST('2024-02-08' AS DATE)), (CAST('2024-02-17' AS DATE)), (CAST('2024-02-20' AS DATE)),
        (CAST('2024-03-03' AS DATE)), (CAST('2024-03-07' AS DATE)), (CAST('2024-03-15' AS DATE)),
        (CAST('2024-03-24' AS DATE)), (CAST('2024-03-30' AS DATE)), (CAST('2024-04-03' AS DATE)),
        (CAST('2024-04-14' AS DATE)), (CAST('2024-04-15' AS DATE)), (CAST('2024-04-26' AS DATE)),
        (CAST('2024-05-01' AS DATE)), (CAST('2024-05-06' AS DATE)), (CAST('2024-05-17' AS DATE)),
        (CAST('2024-05-22' AS DATE)), (CAST('2024-05-31' AS DATE)), (CAST('2024-06-08' AS DATE)),
        (CAST('2024-06-16' AS DATE)), (CAST('2024-06-18' AS DATE)), (CAST('2024-06-29' AS DATE)),
        (CAST('2024-07-02' AS DATE)), (CAST('2024-07-14' AS DATE)), (CAST('2024-07-15' AS DATE)),
        (CAST('2024-07-27' AS DATE)), 
        (CAST('2024-07-31' AS DATE))
    ) AS t(date)
),

failed_non_vote_transactions AS (
    SELECT fee, 'failed' as status
    FROM solana.transactions t
    WHERE success = false
    AND EXISTS (
        SELECT 1 FROM dates d
        WHERE t.block_time >= CAST(d.date AS TIMESTAMP)
        AND t.block_time < CAST(d.date AS TIMESTAMP) + INTERVAL '1' DAY
    )
),
success_non_vote_transactions AS (
    SELECT fee, 'success' as status
    FROM solana.transactions t
    WHERE success = true
    AND EXISTS (
        SELECT 1 FROM dates d
        WHERE t.block_time >= CAST(d.date AS TIMESTAMP)
        AND t.block_time < CAST(d.date AS TIMESTAMP) + INTERVAL '1' DAY
    )
)
    -- AND block_time BETWEEN CAST(DATE {{start_date}} AS TIMESTAMP) AND CAST(DATE {{start_date}} + INTERVAL '1' DAY AS TIMESTAMP)

SELECT 
    status,
    COUNT(*) as count,
    MIN(fee) as min_fee,
    MAX(fee) as max_fee,
    ROUND(AVG(fee), 2) as mean_fee,
    ROUND(APPROX_PERCENTILE(fee, 0.5), 2) as median_fee,
    ROUND(APPROX_PERCENTILE(fee, 0.25), 2) as q1_fee,
    ROUND(APPROX_PERCENTILE(fee, 0.75), 2) as q3_fee
FROM (
    SELECT * FROM failed_non_vote_transactions
    UNION ALL
    SELECT * FROM success_non_vote_transactions
)
GROUP BY status;
"""

def fee(dune: DuneClient) -> pd.DataFrame:
    query_result = execute_dune_query(dune, FEE_QUERY_ID, [], "medium")
    return query_result

if __name__ == "__main__":
    output_dir = "/data0/xiaoyez/Solana_Ecosystem/data/fee/"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    dune = init_dune_client()
    query_result = fee(dune)
    query_result.to_csv(f"{output_dir}/fee.csv", index=False)

    print(query_result)

# 00:34 01JHX48JBJ19TZKXPNXQBNSYEN
# 08:39 - 08:49 01JHY00ECQBS0FNPJEF6MP2APW