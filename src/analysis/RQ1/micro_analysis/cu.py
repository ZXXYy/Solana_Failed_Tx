import os
import argparse
import pandas as pd
from dune_api import execute_dune_query, init_dune_client
from dune_client.client import DuneClient

# https://dune.com/queries/4586852
CU_QUERY_ID = 4586852
CU_QUERY_FOR_REF = """
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
    SELECT 
    t.meta.computeunitsconsumed as cu,
    t.meta.fee as fee,
    CASE 
        WHEN t.meta.computeunitsconsumed > 0 
        THEN CAST(t.meta.fee AS DOUBLE) / CAST(t.meta.computeunitsconsumed AS DOUBLE)
        ELSE NULL 
    END as fee_per_cu, 
    'failed' as status
    FROM solana.raw_0003 r
    CROSS JOIN UNNEST(transactions) as t
    WHERE 
        NOT contains(t.transaction.message.accountkeys, 'Vote111111111111111111111111111111111111111')
        AND EXISTS (
            SELECT 1 FROM dates d
            WHERE r.blocktime >= to_unixtime(CAST(d.date AS TIMESTAMP))
            AND r.blocktime < to_unixtime(CAST(d.date AS TIMESTAMP) + INTERVAL '1' DAY)
        )
        AND t.meta.err is not null
),
success_non_vote_transactions AS (
    SELECT 
    t.meta.computeunitsconsumed as computeunitsconsumed,
    t.meta.fee as fee,
    CASE 
        WHEN t.meta.computeunitsconsumed > 0 
        THEN CAST(t.meta.fee AS DOUBLE) / CAST(t.meta.computeunitsconsumed AS DOUBLE)
        ELSE NULL 
    END as fee_per_cu,
    'success' as status
    FROM solana.raw_0003 r
    CROSS JOIN UNNEST(transactions) as t
    WHERE 
        NOT contains(t.transaction.message.accountkeys, 'Vote111111111111111111111111111111111111111')
        AND EXISTS (
            SELECT 1 FROM dates d
            WHERE r.blocktime >= to_unixtime(CAST(d.date AS TIMESTAMP))
            AND r.blocktime < to_unixtime(CAST(d.date AS TIMESTAMP) + INTERVAL '1' DAY)
        )
        AND t.meta.err is null
)

SELECT 
    status,
    COUNT(*) as count,
    -- Fee statistics
    MIN(fee) as min_fee,
    MAX(fee) as max_fee,
    ROUND(AVG(fee), 2) as mean_fee,
    ROUND(APPROX_PERCENTILE(fee, 0.5), 2) as median_fee,
    APPROX_PERCENTILE(fee, ARRAY[0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 
                                0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]) as fee_percentiles,
    -- CU statistics
    MIN(cu) as min_cu,
    MAX(cu) as max_cu,
    ROUND(AVG(cu), 2) as mean_cu,
    ROUND(APPROX_PERCENTILE(cu, 0.5), 2) as median_cu,
    APPROX_PERCENTILE(cu, ARRAY[0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 
                                0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]) as cu_percentiles,
    -- Fee per CU statistics
    ROUND(MIN(fee_per_cu), 8) as min_fee_per_cu,
    ROUND(MAX(fee_per_cu), 8) as max_fee_per_cu,
    ROUND(AVG(fee_per_cu), 8) as mean_fee_per_cu,
    ROUND(APPROX_PERCENTILE(fee_per_cu, 0.5), 8) as median_fee_per_cu,
    APPROX_PERCENTILE(fee_per_cu, ARRAY[0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 
                                0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]) as fee_per_cu_percentiles
FROM (
    SELECT * FROM failed_non_vote_transactions
    UNION ALL
    SELECT * FROM success_non_vote_transactions
)
GROUP BY status;
"""

def cu(dune: DuneClient) -> pd.DataFrame:
    query_result = execute_dune_query(dune, CU_QUERY_ID, [], "medium")
    return query_result

def parser_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output_filename", type=str, default="cu")
    parser.add_argument("--first_half", action="store_true")
    parser.add_argument("--second_half", action="store_true")
    return parser.parse_args()

if __name__ == "__main__":
    args = parser_args()
    half = None
    if args.first_half:
        half = "first_half"
    elif args.second_half:
        half = "second_half"
    else:
        half = "all"
    
    output_dir = f'/data0/xiaoyez/Solana_Ecosystem/data/cu/{half}'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    output_filename = os.path.join(output_dir, args.output_filename+".csv")
    
    dune = init_dune_client()
    
    query_result = cu(dune)
    query_result.to_csv(output_filename, index=False)

    print(query_result)

# 09:03 01JHY1CJTBC0K4M6B731PDMZ3F all 10 percentiles failed 
# 10:05 01JHY4XE5PYVV5BA47GHTVGPCS first half 10 percentiles  failed
# 11:16 