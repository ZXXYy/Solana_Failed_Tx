import colorsys
import os
import sys
import time
import logging
import pymongo
import cudf
import cupy as cp
import argparse
from cuml.cluster import KMeans, HDBSCAN
from cuml.preprocessing import StandardScaler, MinMaxScaler
from cuml.decomposition import PCA
# from sklearn.preprocessing import MinMaxScaler
from cuml.metrics.cluster.silhouette_score import cython_silhouette_score  # 使用 cuML 的实现
from cuml.neighbors import NearestNeighbors  # 替换 sklearn 版本

from sklearn.metrics import silhouette_score 
from matplotlib.colors import ListedColormap
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.utils import shuffle
from tqdm import tqdm
from scipy.cluster.hierarchy import linkage, fcluster
# from sklearn.neighbors import NearestNeighbors
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier

from signer_feature_extraction import DB_TABLE_SIGNER_FEATURES
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utils.utils import get_db_client, timer, db_table_exists, setup_logger

MANUAL_VERIFICATION_FILE_NAME = '/data0/xiaoyez/Solana_Ecosystem/data/manual_signer_labels.csv'
BOT_MANUAL_VERIFICATION_FILE_NAME = '/data0/xiaoyez/Solana_Ecosystem/data/cluster_signer_labels_bot_dt.csv'
HUMAN_MANUAL_VERIFICATION_FILE_NAME = '/data0/xiaoyez/Solana_Ecosystem/data/cluster_signer_labels_human_dt.csv'
DB_TABLE_SIGNER_LABELS = 'signer_labels_one_year_decision_tree'

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--use_gpu", action="store_true", help="use GPU for clustering")
    parser.add_argument("--silhouette_score", action="store_true", help="use silhouette score for clustering")
    parser.add_argument("--sample4manual", action="store_true", help="sample for manual verification")
    parser.add_argument("--verify_label", action="store_true", help="verify signer label")
    parser.add_argument("--debug", action="store_true", help="debug mode")

    return parser.parse_args()

def random_sample_for_manual_verification(mydb, num_samples=100):
    df_signer_labels = pd.read_csv(MANUAL_VERIFICATION_FILE_NAME)
    gt_signer = df_signer_labels['signer'].tolist()

    if os.path.exists(BOT_MANUAL_VERIFICATION_FILE_NAME):
        df_signer_labels = pd.read_csv(BOT_MANUAL_VERIFICATION_FILE_NAME)
        # update df_signer_labels
        for i, row in tqdm(df_signer_labels.iterrows(), total=len(df_signer_labels)):
            signer_labels = mydb[DB_TABLE_SIGNER_LABELS].find_one({"signer": row["signer"]})
            if signer_labels is None:
                print(f"signer {row['signer']} not found in db")
                df_signer_labels.at[i, "label"]  = -1
                continue
            df_signer_labels.at[i, "label"] = signer_labels["label"]
        df_signer_labels.to_csv(BOT_MANUAL_VERIFICATION_FILE_NAME, index=False)
    else:
        df_signer_labels = pd.DataFrame(list(mydb[DB_TABLE_SIGNER_LABELS].aggregate([
            { "$match": { "label": { "$in": [1] } } },
            { "$match": { "signer": { "$nin": gt_signer } } },
            { "$sample": { "size": num_samples } }
        ])))
        df_signer_labels['manual_verification'] = None 
        df_signer_labels.to_csv(BOT_MANUAL_VERIFICATION_FILE_NAME, index=False)

    if os.path.exists(HUMAN_MANUAL_VERIFICATION_FILE_NAME):
        df_signer_labels = pd.read_csv(HUMAN_MANUAL_VERIFICATION_FILE_NAME)
        # update df_signer_labels
        for i, row in tqdm(df_signer_labels.iterrows(), total=len(df_signer_labels)):
            signer_labels = mydb[DB_TABLE_SIGNER_LABELS].find_one({"signer": row["signer"]})
            if signer_labels is None:
                print(f"signer {row['signer']} not found in db")
                df_signer_labels.at[i, "label"]  = -1
                continue
            df_signer_labels.at[i, "label"] = signer_labels["label"]
        df_signer_labels.to_csv(HUMAN_MANUAL_VERIFICATION_FILE_NAME, index=False)
    else:
        df_signer_labels_human = pd.DataFrame(list(mydb[DB_TABLE_SIGNER_LABELS].aggregate([
            { "$match": { "label": { "$in": [0] } } },
            { "$match": { "signer": { "$nin": gt_signer } } },
            { "$sample": { "size": num_samples } }
        ])))
        df_signer_labels_human['manual_verification'] = None
        df_signer_labels_human.to_csv(HUMAN_MANUAL_VERIFICATION_FILE_NAME, index=False)

if __name__ == "__main__":
    args = parse_args()
    global logger
    logger = setup_logger(level=logging.DEBUG if args.debug else logging.INFO, name="signer_clustering")
    myclient, mydb, txs_table = get_db_client()
    start_time = time.time()
    if args.sample4manual and db_table_exists(mydb, DB_TABLE_SIGNER_LABELS):
        random_sample_for_manual_verification(mydb, num_samples=100)
        exit()

    # read feature data
    with timer("Read feature data"):
        signer_features = mydb[DB_TABLE_SIGNER_FEATURES]
        if args.debug:
            df_features = pd.DataFrame(list(mydb[DB_TABLE_SIGNER_FEATURES].find().limit(10000)))
        else:
            df_features = pd.DataFrame(list(mydb[DB_TABLE_SIGNER_FEATURES].find()))
    # # if #tx is 1, it is hard to consider it is bot or human, drop it
    # df_features = df_features[df_features['total_txs'] > 10]
    # logger.info(df_features.columns)
    df_features = df_features.dropna()
    # df_features_knn = df_features.drop(columns=['_id', 'signer', 'active_time', 'interval_12h_mean', 'interval_12h_variance', 'max_interval', 'total_blocks']) # drop signer column
    df_features = df_features.drop(columns=[
        'interval_mean', 'interval_variance', 
        'interval_24h_mean', 'interval_24h_variance',
        'total_failed_txs', 'failed_txs_per_block',
    ])

    # read ground truth
    df_signer_labels = pd.read_csv(MANUAL_VERIFICATION_FILE_NAME)
    df_signer_labels['label'] = df_signer_labels['manual_verification'].apply(lambda x: 1 if x=='BOT' else 0)
    # get signer feature from df_features
    df_train_features = df_features[df_features['signer'].isin(df_signer_labels['signer'])]
    # merge df_train_features and df_signer_labels
    df_train = df_train_features.merge(df_signer_labels, on='signer')
    # split df_train into train and test
    df_train_X = df_train.drop(columns=['signer', 'label', 'manual_verification', '_id_x', '_id_y'])
    df_train_y = df_train['label']
    print(df_train_X.columns)
    df_test = df_features[~df_features['signer'].isin(df_signer_labels['signer'])]
    df_test_X = df_test.drop(columns=['signer', '_id'])

    # train decision tree
    clf = RandomForestClassifier(n_estimators=50)
    clf.fit(df_train_X, df_train_y)

    # predict test data
    df_test_y_pred = clf.predict(df_test_X)
    df_test['label'] = df_test_y_pred
    print(pd.Series(df_test_y_pred).value_counts())
    probabilities = clf.predict_proba(df_test_X)
    df_test['probability'] = probabilities[:, 1]
    df_test = df_test[(df_test['probability'] > 0.7) | (df_test['probability'] < 0.3)]
    print(df_test['label'].value_counts())
    df_test = df_test[(df_test['probability'] > 0.8) | (df_test['probability'] < 0.2)]
    print(df_test['label'].value_counts())
    df_test = df_test[(df_test['probability'] > 0.9) | (df_test['probability'] < 0.1)]
    print(df_test['label'].value_counts())

    df_test = df_test[["_id", "signer", "label"]]
    mydb[DB_TABLE_SIGNER_LABELS].drop()
    mydb[DB_TABLE_SIGNER_LABELS].insert_many(df_test.to_dict('records'))
    end_time = time.time()
    logger.info(f"Time taken: {end_time - start_time} seconds")
