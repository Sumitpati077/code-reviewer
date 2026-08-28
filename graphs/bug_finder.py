from langchain_ollama import ChatOllama
from langchain_anthropic import ChatAnthropic
from responses.agent_comment import AgentReview
from responses.agent_state import ReviewState, PullRequestDetailState

llm = ChatOllama(
  model='qwen3.5:2b'
).with_structured_output(AgentReview)

from langchain.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END


sys_prompt = """You are an expert software engineer specializing in detecting bugs in Pull Requests.

Your task is to analyze the provided PR diff and identify potential bugs, regressions, and incorrect behavior introduced by the changes.

Focus ONLY on functional correctness. Do not report general formatting, style, or lint issues unless they directly cause incorrect behavior.

## Bug Categories

- Logic Errors: Incorrect conditions, calculations, comparisons, control flow, or return values
- Edge Cases: Empty/null values, missing parameters, boundary conditions, off-by-one errors
- State and Data Issues: Incorrect state updates, unexpected mutations, inconsistent state
- API and Integration Bugs: Incorrect parameters, response handling, error handling, status codes
- Concurrency and Async Bugs: Race conditions, incorrect async/await, wrong execution order
- Error Handling: Incorrectly handled exceptions, silently ignored errors, unexpected failure paths
- Regression Risks: Breaking existing functionality, violating existing assumptions
- Resource and Lifecycle Bugs: Resources not released, incorrect connection/session handling

## Important Rules

- Only report issues that are reasonably likely to be real bugs.
- Do not report speculative problems without evidence from the code.
- Do not report stylistic preferences, formatting, or lint issues.
- Do not report security issues unless they directly result in functional incorrectness.
- Consider the surrounding code when determining whether something is actually a bug.
- Pay particular attention to newly added or modified lines.
- Do not invent bugs simply to produce findings.

## Severity Levels

- critical: Complete functional breakdown, data loss, or production crash
- high: Significant incorrect behavior affecting core functionality
- medium: Incorrect behavior in non-critical paths or specific conditions
- low: Minor incorrect behavior with limited impact

## Output Format

You MUST return a JSON object with a "comments" array. Each comment object must have exactly these fields:

- title: Short, specific description of the bug
- description: Detailed explanation of why this is a bug and what incorrect behavior it causes
- category: One of "bug", "lint", "security", "performance", "code_quality", "maintainability", "testing", "documentation", "style", "other"
- severity: One of "critical", "high", "medium", "low", "info"
- file_path: Path of the file containing the issue
- lines: Affected line or line range, e.g. "42" or "42-48"
- suggestion: Recommended fix
- rationale: Reasoning explaining why the suggested change is appropriate
- suggested_code: Optional example of corrected code, or null

If no significant bugs are found, return an empty comments array.
"""

user_input: str = ""

def _get_user_prompt(state: ReviewState):
    """Prompt the user for input and return it as a HumanMessage."""
    
    file_diff = state["file_diff"]
    return {
        "messages": [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=f"""
Revie the following PR diff for bugs:
```diff
{file_diff}
```
Report the bugs you find.
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

graph.get_graph().draw_mermaid_png(output_file_path="images/bug_finder.png")

def bug_finder_agent(input_state: PullRequestDetailState):
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
 