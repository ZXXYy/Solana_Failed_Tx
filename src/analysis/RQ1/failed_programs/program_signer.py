import os
import pandas as pd
from dune_api import execute_dune_query, init_dune_client
from dune_client.client import DuneClient

# https://dune.com/queries/4587690
PROGRAM_SIGNER_QUERY_ID = 4587690
PROGRAM_SIGNER_QUERY_FOR_REF_TIMEOUT = """
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

failed_transactions AS (
    SELECT DISTINCT t.signer
    FROM solana.transactions t
    WHERE success = FALSE
    AND log_messages[CARDINALITY(log_messages)] LIKE 'Program {{program_id}} failed:%'
    AND EXISTS (
        SELECT 1 FROM dates d
        WHERE t.block_time >= CAST(d.date AS TIMESTAMP)
        AND t.block_time < CAST(d.date AS TIMESTAMP) + INTERVAL '1' DAY
    )
)

SELECT COUNT(*) as unique_signer_count
FROM failed_transactions;
"""

def program_signer(dune, program_id: str) -> pd.DataFrame:
    query_result = execute_dune_query(dune, PROGRAM_SIGNER_QUERY_ID, {'program_id': f"\'{program_id}\'", 'program_id_str': f"{program_id}"}, "medium")
    return query_result

if __name__ == "__main__":
    output_dir = "/data0/xiaoyez/Solana_Ecosystem/data/program_signer/"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    top_failed_program_path = "/data0/xiaoyez/Solana_Ecosystem/data/top_failed_program/top_failed_program.csv"
    top_failed_program_df = pd.read_csv(top_failed_program_path)
    
    
    dune = init_dune_client()

    program_ids = top_failed_program_df["program_id"].tolist()[:15]
    program_ids = program_ids[::-1]
    for program_id in program_ids:
        if os.path.exists(f"{output_dir}/{program_id}.csv"):
            print(f"{program_id} already exists")
            continue
        query_result = program_signer(dune, program_id)
        query_result.to_csv(f"{output_dir}/{program_id}.csv", index=False)

    print(query_result)

# 00:26 01JHX3T1CCMRNR59S3GWED7T19