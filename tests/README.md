# Test Cases

## Quick Start

```shell
python -m pip install pytest
export GENTRADE_CACHE_DIR=
export BINANCE_API_KEY=
export BINANCE_API_SECRET=

pytest --log-cli-level=INFO -s test_llm.py
pytest --log-cli-level=INFO -s test_llm.py::test_llm_tools
pytest --log-cli-level=INFO -s test_llm.py::test_llm_tools[gemini-2.0-flash]
```
