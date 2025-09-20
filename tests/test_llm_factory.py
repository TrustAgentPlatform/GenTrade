"""
Tests for LLM Tool Integration

This module contains pytest fixtures and test cases to verify the integration
of various Large Language Models (LLMs) with tool calling capabilities.

The tests validate that different LLMs can correctly:
1. Receive tool definitions through the bind_tools method
2. Generate appropriate tool calls when presented with queries requiring computation
3. Process tool responses to form final answers

Fixtures:
- llm_factory: Provides a module-level LLMFactory instance for creating LLM instances
- llm_instance: Parameterized module-level fixture that creates specific LLM instances
  from different providers (Dashscope, OpenRouter, SiliconFlow, Ollama) with various models

Test Cases:
- test_tool_basic: Verifies basic tool calling functionality using addition and multiplication
  tools, ensuring proper tool invocation and response processing
"""

import pytest

from langchain_core.tools import tool
from langchain_core.messages import ToolMessage

from gentrade.llm.factory import LLMFactory

@pytest.fixture(scope="module")
def llm_factory():
    return LLMFactory()

@pytest.fixture(params=[
    {
        "provider": "dashscope",
        "model": "qwen-turbo",
        "temperature": 0.1
    },
    {
        "provider": "dashscope",
        "model": "deepseek-r1",
        "temperature": 0.1
    },
    {
        "provider": "openrouter",
        "model": "anthropic/claude-3.5-sonnet",
        "temperature": 0.1
    },
    {
        "provider": "openrouter",
        "model": "meta-llama/llama-4-scout:free",
        "temperature": 0.1
    },
    {
        "provider": "openrouter",
        "model": "google/gemini-2.0-flash-001",
        "temperature": 0.1
    },
    {
        "provider": "siliconflow",
        "model": "THUDM/glm-4-9b-chat",
        "temperature": 0.1
    },
    {
        "provider": "ollama",
        "model": "qwen2.5",
        "temperature": 0.1
    },
], ids=["qwen-turbo", "deepseek-r1", "claude-3.5-sonnet", \
        "llama-4-scout", "gemini-2.0-flash", "glm-4-9b-chat", \
        "qwen2.5-local"],
    scope="module")
def llm_instance(request, llm_factory):
    config = request.param
    print(config)
    return llm_factory.llm(config['provider'], config['model'], config['temperature'])


def test_tool_basic(llm_instance):
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

    llm_with_tools = llminst.bind_tools(tools)

    query = "What is 15 * 3? Also, add 10 to 45."
    response = llm_with_tools.invoke(query)
    print(response)

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
