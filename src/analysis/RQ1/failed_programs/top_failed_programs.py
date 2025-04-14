import os
import pandas as pd
from dune_api import execute_dune_query, init_dune_client
from dune_client.client import DuneClient

# https://dune.com/queries/4587144
TOP_FAILED_PROGRAM_QUERY_ID = 4587144
TOP_FAILED_PROGRAM_QUERY_FOR_REF = """
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

extracted_program_errors AS (
  SELECT
    REGEXP_EXTRACT(log_messages[CARDINALITY(log_messages)], '^Program ([^ ]+) failed', 1) AS program_id
  FROM solana.transactions t
  WHERE
    success = FALSE
    AND log_messages[CARDINALITY(log_messages)] LIKE 'Program % failed:%'
    AND EXISTS (
        SELECT 1 FROM dates d
        WHERE t.block_time >= CAST(d.date AS TIMESTAMP)
        AND t.block_time < CAST(d.date AS TIMESTAMP) + INTERVAL '1' DAY
    )
)

SELECT
  program_id,
  COUNT(*) AS failed_count
FROM extracted_program_errors
GROUP BY
  program_id
ORDER BY
  failed_count DESC;
"""

def top_failed_program(dune) -> pd.DataFrame:
    query_result = execute_dune_query(dune, TOP_FAILED_PROGRAM_QUERY_ID, {}, "medium")
    return query_result

if __name__ == "__main__":
    output_dir = "/data0/xiaoyez/Solana_Ecosystem/data/top_failed_program/"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    dune = init_dune_client()
    query_result = top_failed_program(dune)
    query_result.to_csv(f"{output_dir}/top_failed_program.csv", index=False)

    print(query_result)
