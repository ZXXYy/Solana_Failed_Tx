import os
import time
import pymongo
import logging
from contextlib import contextmanager
from logging.handlers import TimedRotatingFileHandler

def setup_logger(level=logging.INFO, name=None):
    filename = os.path.basename(__file__).split('.')[0]
    logger = logging.getLogger(name) if name else logging.getLogger(filename)
    logger.setLevel(level)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if not os.path.exists(f'logs/'):
        os.makedirs(f'logs/')

    file_handler =  TimedRotatingFileHandler(
        filename=f'logs/{filename}.log',
        when='midnight',  # 每天午夜切换文件
        interval=1,       # 间隔为1天
        backupCount=7,    # 保留7天的日志文件
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger

logger = setup_logger()

def deprecated(func):
    def wrapper(*args, **kwargs):
        logger.warning(f"Function {func.__name__} is deprecated")
        return func(*args, **kwargs)
    return wrapper

@contextmanager
def timer(name="", logger=logger, level=logging.INFO):
    start = time.perf_counter()
    yield
    end = time.perf_counter()
    logger.log(level, f"{name} execution time: {end - start:.4f} seconds")

def get_db_client():
    myclient = pymongo.MongoClient("mongodb://localhost:27018/")
    mydb = myclient["solana"]
    txs_table = mydb["txs_one_year"]
    return myclient, mydb, txs_table

def db_table_exists(mydb, table_name):
    return table_name in mydb.list_collection_names()

if __name__ == "__main__":
    logger.info("test")