"""
Test LLM compatible call on ChatOpenAI and tools usage.

- Prerequisites:
    pip install -r langchain_openai langchain_core langchain_tavily langchain langgraph
    expose DASHSCOPE_API_KEY=your_api_key
    expose OPENROUTER_API_KEY=your_api_key
    expose SILICONFLOW_API_KEY=your_api_key
    expose TAVILY_API_KEY=your_api_key

- Run:
    pytest --log-cli-level=INFO -s test_llm.py

- Output:


"""

from typing import Optional
from typing_extensions import TypedDict

from pydantic import BaseModel, Field

from langchain_core.tools import tool
from langchain_core.messages import ToolMessage

from langchain_tavily import TavilySearch
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph, START, END

from fixture_llm import llm_instance                # pylint: disable=unused-import

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

        # 绑定工具
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


def test_agent(llm_instance):
    llminst = llm_instance

    # Create the agent
    memory = MemorySaver()
    search = TavilySearch(max_results=2)
    tools = [search]
    agent_executor = create_react_agent(llminst, tools, checkpointer=memory)

    config = {"configurable": {"thread_id": "abc123"}}

    input_message = {
        "role": "user",
        "content": "Search for the weather in SF",
    }

    for step in agent_executor.stream({"messages": [input_message]}, config, stream_mode="values"):
        step["messages"][-1].pretty_print()


def test_tool_tavily_search(llm_instance):
    llminst = llm_instance

    search = TavilySearch(max_results=2)
    response = search.invoke("What's the weather where I live?")
    print(response)

    tools = [search]
    tool_map = {"tavily_search": search}
    llm_with_tools = llminst.bind_tools(tools)

    query = "Search for the weather in SF"
    response = llm_with_tools.invoke([{"role": "user", "content": query}])
    print(response)

    tool_messages = []

    for tool_call in response.tool_calls:
        print(tool_call)
        tool_output = tool_map[tool_call['name']].invoke(tool_call['args'])
        tool_messages.append(ToolMessage(tool_output, tool_call_id=tool_call['id']))

    final_response = llm_with_tools.invoke([query, response] + tool_messages)
    print(final_response.content)


class WeatherInfo(BaseModel):
    """Weather information to tell user."""

    weather: str = Field(description="weather condition, e.g., sunny, rainy")
    temperature: str = Field(description="temperature in Fahrenheit or Celsius")
    humidity: str = Field(description="humidity percentage")

class Joke(BaseModel):
    """Joke to tell user."""

    setup: str = Field(description="The setup of the joke")
    punchline: str = Field(description="The punchline to the joke")
    rating: Optional[float] = Field(  # 改为float类型，支持小数评分
        default=None, description="How funny the joke is, from 1 to 10 (can be a decimal)"
    )

def test_tool_structured_output(llm_instance):
    """
    This may not work for deepseek model, since there a json prefix in its' output like:

    data = 'Here\'s a JSON object with a cat joke for you:\n\n```json\n{\n
    "setup": "Why did the cat sit on the computer?",\n
    "punchline": "To keep an eye on the mouse!",\n    "rating": 4.5\n}\n```'
    """
    structured_llm = llm_instance.with_structured_output(
        Joke, method="json_schema")

    prompt = """
    Tell me a joke about cats. Return the result as a JSON object
    with setup, punchline, and optional rating fields.
    Following is an example of json output
    {
        "setup": "setup of joke",
        "punchline": "punchline of joke",
        "rating": 1.0
    }
    """
    response = structured_llm.invoke(prompt)
    print("Joke Setup:", response.setup)
    print("Joke Punchline:", response.punchline)
    if response.rating is not None:
        print("Joke Rating:", response.rating)

# Graph state
class State(TypedDict):
    topic: str
    joke: str
    improved_joke: str
    final_joke: str

def test_llm_graph(llm_instance):

    # Nodes
    def generate_joke(state: State):
        """First LLM call to generate initial joke"""

        msg = llm_instance.invoke(f"Write a short joke about {state['topic']}")
        return {"joke": msg.content}


    def check_punchline(state: State):
        """Gate function to check if the joke has a punchline"""

        # Simple check - does the joke contain "?" or "!"
        if "?" in state["joke"] or "!" in state["joke"]:
            return "Pass"
        return "Fail"


    def improve_joke(state: State):
        """Second LLM call to improve the joke"""

        msg = llm_instance.invoke(f"Make this joke funnier by adding wordplay: {state['joke']}")
        return {"improved_joke": msg.content}


    def polish_joke(state: State):
        """Third LLM call for final polish"""

        msg = llm_instance.invoke(f"Add a surprising twist to this joke: {state['improved_joke']}")
        return {"final_joke": msg.content}

    # Build workflow
    workflow = StateGraph(State)

    # Add nodes
    workflow.add_node("generate_joke", generate_joke)
    workflow.add_node("improve_joke", improve_joke)
    workflow.add_node("polish_joke", polish_joke)

    # Add edges to connect nodes
    workflow.add_edge(START, "generate_joke")
    workflow.add_conditional_edges(
        "generate_joke", check_punchline, {"Fail": "improve_joke", "Pass": END}
    )
    workflow.add_edge("improve_joke", "polish_joke")
    workflow.add_edge("polish_joke", END)

    # Compile
    chain = workflow.compile()

    # Show workflow
    #display(Image(chain.get_graph().draw_mermaid_png()))

    # Invoke
    state = chain.invoke({"topic": "cats"})
    print("Initial joke:")
    print(state["joke"])
    print("\n--- --- ---\n")
    if "improved_joke" in state:
        print("Improved joke:")
        print(state["improved_joke"])
        print("\n--- --- ---\n")

        print("Final joke:")
        print(state["final_joke"])
    else:
        print("Joke failed quality gate - no punchline detected!")
