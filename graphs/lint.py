from langchain_ollama import ChatOllama
from langchain_anthropic import ChatAnthropic

llm = ChatOllama(
  model='qwen3.5:2b'
)

llm.with_structured_output()

from langchain.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import MessagesState, StateGraph, START, END

class LintState(MessagesState):
    file_diff: str


sys_prompt = """
You are a helpful assistant that checks the lint of a PR diff.

Major responsibilities:

- Check standard linting.
- Identify only syntax issues.
- Identify only style violations.
- Identify only common linting problems.
"""

user_input: str = ""

def _get_user_prompt(state: LintState):
    """Prompt the user for input and return it as a HumanMessage."""
    
    file_diff = state["file_diff"]
    return {
        "messages": [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=f"""
Revie the following PR diff for linting issues:
```diff
{file_diff}
```
Report the linting issues you find.
                         """)
        ]
    }

def _calling_llm(state: LintState):
    return { "messages": [llm.invoke(state["messages"])]}
  
builder = StateGraph(LintState)
builder.add_node("get_user_prompt", _get_user_prompt)
builder.add_node("calling_llm", _calling_llm)

config = {"configurable": {"thread_id": 1}}


builder.add_edge(START, "get_user_prompt")
builder.add_edge("get_user_prompt", "calling_llm")
builder.add_edge("calling_llm", END)

from langgraph.checkpoint.memory import MemorySaver
memory = MemorySaver()
graph = builder.compile(checkpointer=memory)

graph.get_graph().draw_mermaid_png(output_file_path="images/lint.png")

def lint_agent(file_diff: str):
    result = graph.invoke(
        {
            "file_diff": file_diff,
            "messages": [],
        },
        config=config
    )
    print(result['messages'][-1].content)