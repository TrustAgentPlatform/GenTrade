# Trust Investment Agent

![](./docs/overview.png)

## Agents

TBD

## Services

### OHLCV DataHub

- Start Server
```shell
# Pull image
docker pull registry.cn-hangzhou.aliyuncs.com/kenplusplus/tia_datahub

# Create .env file from .env_template

# Run OHLCV datahub service
docker run -p 8000:8000 \
    --env-file=.env -v <data folder>:/data \
    registry.cn-hangzhou.aliyuncs.com/kenplusplus/tia_datahub
```

- Client Test
```shell
curl -X 'GET' \
  'http://127.0.0.1:8000/markets/?market_type=all' \
  -H 'accept: application/json'

curl -X 'GET' \
  'http://127.0.0.1:8000/assets/?market_id=b13a4902-ad9d-11ef-a239-00155d3ba217&start=0&max_count=1000' \
  -H 'accept: application/json'

curl -X 'GET' \
  'http://127.0.0.1:8000/asset/get_ohlcv?market_id=b13a4902-ad9d-11ef-a239-00155d3ba217&asset=BTC_USDT&timeframe=1m&since=-1&limit=10' \
  -H 'accept: application/json'
```