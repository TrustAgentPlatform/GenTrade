"""
Test LLM compatible call on ChatOpenAI and tools usage.

pip install -r langchain_openai langchain_core

"""
import os
import time
import pytest

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage


class CustomChatOpenAI(ChatOpenAI):

    def invoke(self, messages, config=None, **kwargs):
        start_time = time.perf_counter()

        response = super().invoke(messages, config=config, **kwargs)

        duration = time.perf_counter() - start_time
        print(f"Duration: {duration:.2f} seconds")

        token_usage = response.response_metadata["token_usage"]
        print(f"Prompt Tokens: {token_usage.get('prompt_tokens')}")
        print(f"Completion Tokens: {token_usage.get('completion_tokens')}")
        print(f"Total Tokens: {token_usage.get('total_tokens')}")
        return response

@pytest.fixture(params=[
    # 参数1：OpenAI 的 GPT-3.5 模型
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
], ids=["qwen-turbo", "deepseek-r1", "claude-3.5-sonnet", "llama-4-scout", "gemini-2.0-flash"])
def llm_instance(request):
    config = request.param  # 获取当前参数

    if config["provider"] == "dashscope":
        api_key = os.getenv("DASHSCOPE_API_KEY")
        base_url = os.getenv("DASHSCOPE_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1")
    elif config["provider"] == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY")
        base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    else:
        assert False, "Unsupported provider"

    return CustomChatOpenAI(
        model=config["model"],
        temperature=config["temperature"],
        max_tokens=200,
        api_key=api_key,
        base_url=base_url
    )

def test_llm_tools_token_usage(llm_instance):
    llminst = llm_instance

    # Define the tools using the @tool decorator
    @tool
    def add(a: int, b: int) -> int:
        """Adds a and b.
        Args:
            a: The first integer.
            b: The second integer.
        """
        return a + b

    @tool
    def multiply(a: int, b: int) -> int:
        """Multiplies a and b.
        Args:
            a: The first integer.
            b: The second integer.
        """
        return a * b

    tools = [add, multiply]
    tool_map = {"add": add, "multiply": multiply}

        # 绑定工具
    llm_with_tools = llminst.bind_tools(tools)

    query = "What is 15 * 3? Also, add 10 to 45."
    response = llm_with_tools.invoke(query)
    print(response)

    token_usage = response.response_metadata["token_usage"]
    print(f"Prompt Tokens: {token_usage.get('prompt_tokens')}")
    print(f"Completion Tokens: {token_usage.get('completion_tokens')}")
    print(f"Total Tokens: {token_usage.get('total_tokens')}")

    assert response is not None
    assert response.content is not None

    tool_messages = []

    assert len(response.tool_calls) != 0

    for tool_call in response.tool_calls:
        print(tool_call)
        tool_output = tool_map[tool_call['name']].invoke(tool_call['args'])
        tool_messages.append(ToolMessage(tool_output, tool_call_id=tool_call['id']))

    final_response = llm_with_tools.invoke([query, response] + tool_messages)
    print(final_response.content)
