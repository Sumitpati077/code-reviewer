from responses.agent_state import PullRequestDetailState, ReviewState
from langchain.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from graphs.bug_finder import bug_finder_agent
from graphs.lint import lint_agent
from graphs.security import security_agent
from langchain_ollama import ChatOllama
from langchain_anthropic import ChatAnthropic
from responses.agent_comment import AgentReview
import json
import os
from langgraph.types import Overwrite
from datetime import datetime
from prompts import load_prompt

llm = ChatOllama(
  model=os.getenv('MODEL_NAME', 'qwen3.5:2b')
).with_structured_output(AgentReview)

llm = ChatAnthropic(
    model="claude-haiku-4-5-20251001"
).with_structured_output(AgentReview)

sys_prompt = load_prompt("aggregator")

def _get_user_prompt(state: PullRequestDetailState):
    """Prompt the user for input and return it as a HumanMessage."""
    
    reviews = state["reviews"]
    file_diff = state["file_diff"]
    reviews_string = json.dumps(
        [review.model_dump() for review in reviews],
        indent=2
    )
    
    prompt = f"""
    Here are the reviews from the specialized agents:

    {reviews_string}

    Aggregate these reviews into a single review for the diff of the file {state['file_name']}:
    {file_diff}
    """

    return {
        "messages": [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=prompt)
        ]
    }

def _calling_llm(state: PullRequestDetailState):
    review = llm.invoke(state["messages"])
    review = review.comments
    print(review)
    
    return {
      "reviews": Overwrite(review)
    }



builder = StateGraph(PullRequestDetailState)

builder.add_node("bug_finder", bug_finder_agent)
builder.add_node("lint", lint_agent)
builder.add_node("security", security_agent)
builder.add_node("get_user_prompt", _get_user_prompt)
builder.add_node("aggregator", _calling_llm)

builder.add_edge(START, "bug_finder")
builder.add_edge(START, "lint")
builder.add_edge(START, "security")
builder.add_edge("lint", "get_user_prompt")
builder.add_edge("security", "get_user_prompt")
builder.add_edge("bug_finder", "get_user_prompt")
builder.add_edge("get_user_prompt", "aggregator")
builder.add_edge("aggregator", END)



from langgraph.checkpoint.memory import MemorySaver
memory = MemorySaver()
graph = builder.compile(checkpointer=memory)

graph.get_graph().draw_mermaid_png(output_file_path="images/aggregator.png")
config = {"configurable": {"thread_id": "1"}}

def aggregator_agent(file_name: str, file_diff: str):
    result = graph.invoke({
      "file_name": file_name,
      "file_diff": file_diff
    }, config=config)

    return result['reviews']
