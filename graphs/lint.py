from langchain_ollama import ChatOllama
from langchain_anthropic import ChatAnthropic
from responses.agent_comment import AgentReview
from responses.agent_state import ReviewState, PullRequestDetailState

llm = ChatOllama(
  model='qwen3.5:2b'
).with_structured_output(AgentReview)

from langchain.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END


sys_prompt = """You are a linting expert that checks PR diffs for style and syntax issues.

Your task is to analyze the provided PR diff and identify linting violations, style issues, and syntax problems.

## Check For

- Syntax errors and style violations
- Inconsistent naming conventions
- Unused imports or variables
- Incorrect indentation or formatting
- Common linting rule violations

## Severity Levels

- critical: Syntax error that prevents compilation or execution
- high: Style violation that should be fixed before merge
- medium: Minor style inconsistency
- low: Cosmetic or informational suggestion

## Output Format

You MUST return a JSON object with a "comments" array. Each comment object must have exactly these fields:

- title: Short, specific description of the linting issue
- description: Detailed explanation of the linting problem and why it matters
- category: One of "bug", "lint", "security", "performance", "code_quality", "maintainability", "testing", "documentation", "style", "other"
- severity: One of "critical", "high", "medium", "low", "info"
- file_path: Path of the file containing the issue
- lines: Affected line or line range, e.g. "42" or "42-48"
- suggestion: Recommended fix
- rationale: Reasoning explaining why the suggested change is appropriate
- suggested_code: Optional example of corrected code, or null

If no significant linting issues are found, return an empty comments array.
"""

user_input: str = ""

def _get_user_prompt(state: ReviewState):
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
            "file_diff": file_diff,
            "messages": [],
            "review": None
        },
        config=config
    )
    return {"reviews": result['review']['comments']}
