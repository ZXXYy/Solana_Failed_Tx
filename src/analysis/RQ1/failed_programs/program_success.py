import os
import argparse
import pandas as pd
from dune_api import execute_dune_query, init_dune_client
from dune_client.client import DuneClient

# https://dune.com/queries/4587578
PROGRAM_SUCCESS_QUERY_ID = 4587578
PROGRAM_SUCCESS_QUERY_FOR_REF = """

"""

def program_success(dune, program_id: str) -> pd.DataFrame:
    query_result = execute_dune_query(dune, PROGRAM_SUCCESS_QUERY_ID, {'program_id': f"\'{program_id}\'"}, "medium")
    return query_result

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split_num", type=int, required=True)
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()

    output_dir = f"/data0/xiaoyez/Solana_Ecosystem/data/program_success/{args.split_num}"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    top_failed_program_path = "/data0/xiaoyez/Solana_Ecosystem/data/top_failed_program/top_failed_program.csv"
    top_failed_program_df = pd.read_csv(top_failed_program_path)
        
    dune = init_dune_client()

    program_ids = top_failed_program_df["program_id"].tolist()[1:15]
    program_ids = program_ids[::-1]
    for program_id in program_ids:
        if os.path.exists(f"{output_dir}/{program_id[:10]}.csv"):
            print(f"Skipping {program_id} because it already exists")
            continue
        try:
            query_result = program_success(dune, program_id)
            query_result.to_csv(f"{output_dir}/{program_id[:10]}.csv", index=False)
            print(query_result)
        except Exception as e:
            print(f"Error for program {program_id}: {e}")
            continue


# CURRENT EXECUTION ID - start_time = 01:30 FINISH 5:00 01JHX7CYGTY0F1EV77Q67V539T
# CURRENT EXECUTION ID - start_time = 08:36 01JHXZR75M0DKHDDPKTAX8RCAC

