from responses.agent_state import PullRequestDetailState
from langchain.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from graphs.bug_finder import bug_finder_agent
from graphs.lint import lint_agent
from graphs.security import security_agent


builder = StateGraph(PullRequestDetailState)

builder.add_node("bug_finder", bug_finder_agent)
builder.add_node("lint", lint_agent)
builder.add_node("security", security_agent)

builder.add_edge(START, "bug_finder")
builder.add_edge(START, "lint")
builder.add_edge(START, "security")
builder.add_edge("lint", END)
builder.add_edge("security", END)
builder.add_edge("bug_finder", END)


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

    print(result['reviews'])
