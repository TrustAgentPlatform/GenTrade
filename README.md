# GenTrade

The python GenTrade package provide the core functions, model and data to support
GenAI based algorithms trading.


![](./docs/overview.png)


- Install the python package

  ```
  pip install gentrade
  ```
  if you want to try the package from source code you can

  ```
  set PYTHONPATH=<root of gentrade>/src/
  ```

- Then try:

  - [Demos](./demo/): command line based app to show market OHLCV data
  - [Tests](./tests/): test cases for the API and utilities
  - [Apps](./apps/): the application or microservices based on gentrade.


## Demo

_NOTE: please set environment variable like `BINANCE_API_KEY`, `BINANCE_API_SECRET`, \
`OPENAI_API_KEY` before running below demos._

1. Draw the latest 100 hours btcoin's prices (OHLCV)

  ```shell
  cd demo/crypto-cli
  python run_matplot.py -a btc -t 1h -l 100
  ```
  Output:
  ![](docs/demo_crypto_cli_run_matplot.png)

2. Use SMA (Simple Moving Average) to analyze the ETH's prices

  ```shell
  cd demo/crypto-cli
  python run_sma.py -a eth -t 1d -l 200 -g
  ```
  Output:
  ![](docs/demo_crypto_cli_run_sma.png)

3. If want try other strategy like RSI

  ```shell
  cd demo/crypto-cli
  python run_multiple.py -s rsi
  ```
  ![](docs/demo_crypto_cli_run_rsi.png)
  _NOTE: of course you can try more strategies like macd, bb, wma etc_

4. If want ask LLM to select a strategy via a simple prompt like

  - Please get past 400 days price for bitcoin, then different strategy to do
    back testing, and figure out what strategy is the best according to final
    portfolio value
  - 请获取过去300天的以太坊的价格，并使用不同的策略进行回测，最后选出最佳的策略

  ```shell
  cd demo/agent
  python run_auto_strategy.py
  ```
  ![](docs/demo_agent_auto_strategy.png)

5. If want ask LLM to generate strategy according to your idea and do back test,
  for example:
  "请获取过去300天的以太坊的价格，并使用简单平均移动策略来进行回测，在这个策略中，请设置慢线为9，请设置快线为26"

  ![](docs/demo_agent_configure_strategy.png)

## App Services

### OHLCV Data Service

- Start Server

  ```shell
  # Pull image
  docker pull registry.cn-hangzhou.aliyuncs.com/kenplusplus/gentrade_data_serv

  # Create .env file from .env_template

  # Run OHLCV datahub service
  docker run -p 8000:8000 \
      --env-file=.env -v <data folder>:/app/cache \
      registry.cn-hangzhou.aliyuncs.com/kenplusplus/gentrade_data_serv
  ```

- Client Test

  ```shell

  # Get all supported markets
  curl -X 'GET' \
    'http://127.0.0.1:8000/markets/?market_type=all' \
    -H 'accept: application/json'

  # Get all available assets from a specific market
  curl -X 'GET' \
    'http://127.0.0.1:8000/assets/?market_id=b13a4902-ad9d-11ef-a239-00155d3ba217&start=0&max_count=1000' \
    -H 'accept: application/json'

  # Get OHLCV for a specific asset
  curl -X 'GET' \
    'http://127.0.0.1:8000/asset/get_ohlcv?market_id=b13a4902-ad9d-11ef-a239-00155d3ba217&asset=BTC_USDT&timeframe=1m&since=-1&limit=10' \
    -H 'accept: application/json'

  # Start OHLCV collector threading in the background
  curl -X 'POST' \
    'http://127.0.0.1:8000/asset/start_collect?market_id=b13a4902-ad9d-11ef-a239-00155d3ba217&asset=DOGE_USDT&timeframe=1h&since=1732809600' \
    -H 'accept: application/json' \
    -d ''
  ```

The cached data can be found at [this directory](./cache/)
