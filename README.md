Code and sampled dataset for the paper "Why Does My Transaction Fail? A First Look at the Failed Transactions on the Solana Blockchain".
> The complete dataset is approximately 5TB. Due to storage limitations, we only provide a sampled dataset in the repository. To access the full dataset, please use `src/crawl/getBlocks.py` to download it.

## Environment setup
1. Pull the MongoDB Docker container. We use MongoDB, a NoSQL database, to store and query the on-chain data.
    ```
    docker pull mongodb/mongodb-community-server:latest --platform linux/amd64
    docker images
    ```
2. Set up the `docker-compose.yml`
    ```
    version: "3.8"
    services:
            mongodb:
                    image : mongodb/mongodb-community-server
                    container_name: mongodb
                    environment:
                    - PUID=1000
                    - PGID=1000
                    volumes:
                    - <Your_Disk_Storgae_Path>:/data/db
                    ports:
                    - 27017:27017
                    deploy:
                            resources:
                                    limits:
                                            memory: 256G
    ```
3. Start mongodb service
    ```
    docker compose up -d
    ```
4. Setup Python environment.
    ```
    conda create -n solana python=3.12
    conda activate solana
    pip install -r requirements.txt
    ```

## Data Collection & Preprocessing 
The code is under `src/crawler` directory.
1. Config your JSON RPC API in `.env` 
2. Due to the large data volume of Solana transaction data, we sampled one-year transaction data from 2023-08-01 to 2024-0731 and indexed them in `data/sampled_dates.csv` and `data/sampled_dates_with_block_id.csv`. 
    - Run `src/crawler/getSampleDays.py` to get the sampled dates and block ids. The results may differ from the sampled dates we provided due to randomness.
3. Get transactions from the RPC node, process, and store the data into mongodb. 
    The `DEBUG` variable in `.env` can be set to `True` to test the code and crawl only 50 blocks. Otherwise, the code will crawl transactions from block range in `data/sampled_dates_with_block_id.csv`, which takes 7+ days depending on your RPC rate limit.
    ```
    Python src/crwaler/getBlocks.py
    ``` 
We provide a sample of 10,000 transactions in the `data/sample_transactions.json`. Before proceeding with the following steps, write this data to MongoDB. 
```
python src/crawl/insertSample.py
```

## Data Analysis
The code is under `src/analyze` directory. We present the code of the paper in each directory according to the RQs.
When using the sample dataset, update the table name in your code from `txs `to `sample_txs`.

### RQ1 
- Macro-level analysis

    **For Account Types**
    ```
    # extract signer features
    python account_types/signer_feature_extraction.py
    # classifying signers using decision tree
    python account_types/signer_decision_tree.py
    # get signer meta data
    python account_types/failed_signer.py
    # get account types info
    python account_types/initiators.py
    ```

    **For triggering programs**
    ```
    # =====use dune for faster query======
    python failed_programs/top_failed_program.py  # generate data/top_failed_program/top_failed_program.csv
    python failed_program/program_signer.py  # generate data/program_signer/ directory for top failed programs
    python failed_program/program_success.py  # generate data/program_success/ directory for top failed programs
    ```

    **For temporal trends**
    ```
    # ===========
    python time_trend.py # generate data/program_success/ directory for top failed programs
    ```

- Micro-level analysis
    ```
    python cu.py
    python fee.py 
    python index_rank.py
    ```
- use rq1.ipynb to visualize the results in RQ1

### RQ2
1. Extract the error messages from the transactions' log mesaages
    ```
    python error_log.py
    ```
2. We used open card sorting combined with thematic analysis to manually categorize the error log messages in `data/failed_txs.log`, which was generated in step 1. Our categorization results are shown in `data/error_categorization.csv`. The `data/failed_txs.log` file contains error messages, their triggering programs, and the number of failures for each error.
3. Get the statistics for error types
    ```
    python error_type.py
    ```
 
### RQ3
1. Get the top failed programs and their corresponding error types
```
python program_errors.py
```
2. Get the top failed bot/human accounts  and their corresponding error types
```
python account_errors.py
```
