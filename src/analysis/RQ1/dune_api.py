import os
import time
import dotenv
import requests
import pandas as pd

from dune_client.types import QueryParameter
from dune_client.client import DuneClient
from dune_client.query import QueryBase

def init_dune_client():
    os.chdir("/data0/xiaoyez/Solana_Ecosystem/src")
    dotenv.load_dotenv(".env-local")
    dune = DuneClient.from_env()
    return dune


def handle_params(params: dict):
    query_params = []
    for key, value in params.items():
        query_params.append(QueryParameter.text_type(
            name=key,
            value=value
        ))
    return query_params

def execute_dune_query(dune, query_id: int, params: dict, performance: str = "medium"):
    query_params = handle_params(params) if params else []
    query = QueryBase(
        query_id=query_id,
        params=query_params
    )
    query_result = dune.run_query_dataframe(
        query=query,
        performance=performance,
        ping_frequency=5,
    # , ping_frequency = 10 # uncomment to change the seconds between checking execution status, default is 1 second
    # , performance="large" # uncomment to run query on large engine, default is medium
    # , batch_size = 5_000 # uncomment to change the maximum number of rows to retrieve per batch of results, default is 32_000
    ) 

    # Note: to get the result in csv format, call run_query_csv(); for json format, call run_query().

    return query_result

if __name__ == "__main__":
    dune = init_dune_client()
    query_result = execute_dune_query(dune, 4584719, {"start_date": '\'2023-08-09\''})
    print(query_result)