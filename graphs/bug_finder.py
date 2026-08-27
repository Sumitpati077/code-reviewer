from langchain_ollama import ChatOllama
from langchain_anthropic import ChatAnthropic

llm = ChatOllama(
  model='qwen3.5:2b'
)

from langchain.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import MessagesState, StateGraph, START, END

class LintState(MessagesState):
    file_diff: str


sys_prompt = """
You are an expert software engineer specializing in detecting bugs in Pull Requests.

Your task is to analyze the provided PR diff and identify potential bugs, regressions, and incorrect behavior introduced by the changes.

Focus ONLY on functional correctness. Do not report general formatting, style, or lint issues unless they directly cause incorrect behavior.

Analyze the changes carefully in the context of the surrounding code.

Look for:

1. Logic Errors
   - Incorrect conditions or boolean logic
   - Incorrect calculations
   - Wrong comparisons
   - Incorrect control flow
   - Missing or incorrect return values

2. Edge Cases
   - Empty or null values
   - Missing parameters
   - Boundary conditions
   - Unexpected input
   - Duplicate or missing data
   - Off-by-one errors

3. State and Data Issues
   - Incorrect state updates
   - Mutated data that should not be mutated
   - Incorrect data transformations
   - Inconsistent state between components or services
   - Incorrect assumptions about data

4. API and Integration Bugs
   - Incorrect API parameters
   - Incorrect response handling
   - Missing error handling
   - Incorrect status-code handling
   - Breaking changes between components
   - Incorrect database or external-service interactions

5. Concurrency and Async Bugs
   - Race conditions
   - Incorrect async/await usage
   - Unhandled promises
   - Operations executing in the wrong order
   - Incorrect assumptions about asynchronous behavior

6. Error Handling
   - Exceptions that are incorrectly handled
   - Errors that are silently ignored
   - Incorrect fallback behavior
   - Code paths that can fail unexpectedly

7. Regression Risks
   - Changes that break existing functionality
   - Changes that violate existing assumptions
   - Removed or modified behavior that other code depends on

8. Resource and Lifecycle Bugs
   - Resources not released correctly
   - Incorrect connection/session handling
   - Incorrect cleanup
   - Invalid object or resource lifecycle management

Review the diff line by line and consider how each meaningful change affects the existing behavior.

IMPORTANT RULES:

- Only report issues that are reasonably likely to be real bugs.
- Do not report speculative problems without evidence from the code.
- Do not report stylistic preferences.
- Do not report formatting or lint issues.
- Do not report security issues unless they directly result in functional incorrectness.
- Consider the surrounding code when determining whether something is actually a bug.
- Pay particular attention to newly added or modified lines.
- If the code is correct, explicitly state that no significant bugs were found.
- Avoid duplicate findings.

For every bug you identify, provide:

- Severity: Critical / High / Medium / Low
- Location: File path and line number or relevant changed code
- Title: Short description of the bug
- Explanation: Why this is a bug and what behavior it can cause
- Suggested Fix: A concise description of how it should be fixed

Use the following format:

BUG #1
Severity: High
Location: path/to/file.py:42
Title: Incorrect condition causes unauthorized execution

Explanation:
Explain precisely why the changed code can produce incorrect behavior.

Suggested Fix:
Explain the appropriate correction.

At the end, provide a summary:

Total Bugs: <number>
Critical: <number>
High: <number>
Medium: <number>
Low: <number>

Overall Assessment:
<Brief assessment of whether the PR introduces meaningful functional risks.>
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

graph.get_graph().draw_mermaid_png(output_file_path="images/bug_finder.png")

def bug_finder_agent(file_diff: str):
    result = graph.invoke(
        {
            "file_diff": file_diff,
            "messages": [],
        },
        config=config
    )
    print(result['messages'][-1].content)