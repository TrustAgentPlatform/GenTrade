import os
import time
import pytest

from langchain_openai import ChatOpenAI


class CustomChatOpenAI(ChatOpenAI):

    # pylint: disable=redefined-builtin
    def invoke(self, input, config=None, **kwargs):
        start_time = time.perf_counter()

        response = super().invoke(input, config=config, **kwargs)

        duration = time.perf_counter() - start_time
        token_usage = response.response_metadata["token_usage"]
        print(f"[Token] Prompt: {token_usage.get('prompt_tokens')}, "\
              f"Completion: {token_usage.get('completion_tokens')}, "\
              f"Total: {token_usage.get('total_tokens')} "\
              f"[Duration] {duration:.2f} seconds")

        return response

@pytest.fixture(params=[
    {
        "type": "qwen-turbo",
        "provider": "dashscope",
        "model": "qwen-turbo",
        "temperature": 0.1
    },
    {
        "type": "deepseek-r1",
        "provider": "dashscope",
        "model": "deepseek-r1",
        "temperature": 0.1
    },
    {
        "type": "claude-3.5-sonnet",
        "provider": "openrouter",
        "model": "anthropic/claude-3.5-sonnet",
        "temperature": 0.1
    },
    {
        "type": "llama-4-scout",
        "provider": "openrouter",
        "model": "meta-llama/llama-4-scout:free",
        "temperature": 0.1
    },
    {
        "type": "gemini-2.0-flash",
        "provider": "openrouter",
        "model": "google/gemini-2.0-flash-001",
        "temperature": 0.1
    },
    {
        "type": "glm-4-9b-chat",
        "provider": "siliconflow",
        "model": "THUDM/glm-4-9b-chat",
        "temperature": 0.1
    },
    {
        "type": "qwen2.5",
        "provider": "ollama",
        "model": "qwen2.5",
        "temperature": 0.1
    },
], ids=["qwen-turbo", "deepseek-r1", "claude-3.5-sonnet", \
        "llama-4-scout", "gemini-2.0-flash", "glm-4-9b-chat", \
        "qwen2.5-local"],
    scope="module")
def llm_instance(request):
    config = request.param  # 获取当前参数

    if config["provider"] == "dashscope":
        api_key = os.getenv("DASHSCOPE_API_KEY")
        base_url = os.getenv("DASHSCOPE_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1")
    elif config["provider"] == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY")
        base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    elif config["provider"] == "siliconflow":
        api_key = os.getenv("SILICONFLOW_API_KEY")
        base_url = os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
    elif config["provider"] == "ollama":
        api_key = "empty"
        base_url = os.getenv("SILICONFLOW_BASE_URL", "http://localhost:11434/v1")
    else:
        assert False, "Unsupported provider"

    assert api_key is not None, "API key is not set"

    return CustomChatOpenAI(
        model=config["model"],
        temperature=config["temperature"],
        max_tokens=200,
        api_key=api_key,
        base_url=base_url
    )
