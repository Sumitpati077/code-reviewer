from langchain_ollama import ChatOllama
from langchain_anthropic import ChatAnthropic
from responses.agent_comment import AgentReview
from responses.agent_state import ReviewState, PullRequestDetailState
import os

llm = ChatOllama(
  model=os.getenv('MODEL_NAME', 'qwen3.5:2b')
).with_structured_output(AgentReview)

llm = ChatAnthropic(
    model="claude-haiku-4-5-20251001"
).with_structured_output(AgentReview)

from langchain.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from prompts import load_prompt


sys_prompt = load_prompt("lint")

user_input: str = ""

def _get_user_prompt(state: ReviewState):
    """Prompt the user for input and return it as a HumanMessage."""
    
    file_diff = state["file_diff"]
    file_name = state["file_name"]
    return {
        "messages": [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=f"""
Review the following PR diff for linting issues in {file_name}:
```diff
{file_diff}
```
Report the linting issues you find.
                         """)
        ]
    }

def _calling_llm(state: ReviewState):
    review = llm.invoke(state["messages"])
    
    return {
      "review": review
    }
  
builder = StateGraph(ReviewState)
builder.add_node("get_user_prompt", _get_user_prompt)
builder.add_node("calling_llm", _calling_llm)

config = {"configurable": {"thread_id": "1"}}


builder.add_edge(START, "get_user_prompt")
builder.add_edge("get_user_prompt", "calling_llm")
builder.add_edge("calling_llm", END)

from langgraph.checkpoint.memory import MemorySaver
memory = MemorySaver()
graph = builder.compile(checkpointer=memory)

graph.get_graph().draw_mermaid_png(output_file_path="images/lint.png")

def lint_agent(input_state: PullRequestDetailState):
    file_diff = input_state["file_diff"]
    result = graph.invoke(
        {
            "file_name": input_state["file_name"],
            "file_diff": file_diff,
            "messages": [],
            "review": None
        },
        config=config
    )
    return {"reviews": result['review'].comments}
