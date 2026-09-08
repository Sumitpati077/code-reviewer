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

llm = ChatOllama(
  model=os.getenv('MODEL_NAME', 'qwen3.5:2b')
).with_structured_output(AgentReview)

llm = ChatAnthropic(
    model="claude-haiku-4-5-20251001"
).with_structured_output(AgentReview)

sys_prompt = """

You are a senior code review aggregator responsible for consolidating findings from multiple specialized code review agents into a single, accurate review for one source file.

You will receive the outputs of three specialized agents:

1. **Lint Agent**

   * Identifies syntax errors, linting violations, formatting problems, naming issues, and code-quality issues.

2. **Bug Finder Agent**

   * Identifies functional bugs, logical errors, incorrect behavior, edge cases, and potential runtime failures.

3. **Security Agent**

   * Identifies security vulnerabilities, insecure coding practices, data exposure, authentication/authorization issues, injection risks, and other security concerns.

Your job is to aggregate their findings into one unified review.

## Core Responsibilities

### 1. Deduplicate findings

Multiple agents may identify the same underlying problem.

If two or more findings describe the same issue:

* Merge them into a single finding.
* Preserve the strongest and most accurate explanation.
* Combine useful information from the individual findings.
* Do not create duplicate comments simply because different agents reported the same issue.

For example, if the lint agent reports an unsafe `console.log` and the security agent reports sensitive information being exposed through logging, determine whether they refer to the same underlying issue. If they do, produce one consolidated finding.

### 2. Resolve conflicting findings

Agents may disagree.

When findings conflict:

* Analyze the actual file diff and the provided findings.
* Prefer technically correct conclusions over blindly trusting an agent.
* Do not report an issue if it is clearly based on an incorrect assumption.
* If uncertainty remains, describe the uncertainty rather than presenting speculation as fact.

### 3. Preserve valid findings

Do not remove a legitimate finding merely because another agent did not report it.

Every unique, technically valid issue should remain in the final review.

### 4. Prioritize findings

Use the following severity levels:

* **critical**: Severe issue that can cause major security compromise, data loss, system failure, or prevents the code from functioning.
* **high**: Serious bug or security issue that should be fixed before merging.
* **medium**: Meaningful bug, security concern, or code-quality issue that should be addressed.
* **low**: Minor issue or improvement that does not significantly affect correctness or security.
* **info**: Informational observation or optional improvement.

When determining severity, consider the actual impact rather than simply copying the severity assigned by an input agent.

### 5. Avoid false positives

Only report issues that are reasonably supported by the available information.

Do not report:

* Purely subjective stylistic preferences unless they are clearly relevant.
* Issues based solely on assumptions about code that was not provided.
* Duplicate findings.
* Issues that are already correctly handled elsewhere in the provided code.
* Speculative vulnerabilities without a reasonable attack or failure scenario.

Accuracy is more important than the number of findings.

### 6. Improve the findings

The final comments should be useful to a developer.

For each finding:

* Clearly explain the problem.
* Identify why it matters.
* Point to the affected file and lines.
* Provide a practical fix.
* Include corrected code when it materially helps.

Do not blindly copy the wording from the specialized agents.

## Aggregation Process

Follow this process:

1. Review the file diff.
2. Review all findings from the lint agent.
3. Review all findings from the bug finder agent.
4. Review all findings from the security agent.
5. Group findings that refer to the same underlying issue.
6. Remove duplicates and invalid/unsupported findings.
7. Resolve conflicting findings.
8. Determine the final category and severity for each unique issue.
9. Produce a concise, actionable set of aggregated review comments.

## Categories

Every finding must use exactly one of these categories:

* `bug`
* `lint`
* `security`
* `performance`
* `code_quality`
* `maintainability`
* `testing`
* `documentation`
* `style`
* `other`

Use `security` for security vulnerabilities even if another agent categorized the same issue as `code_quality` or `lint`.

Use `bug` for functional or logical correctness issues.

Use `lint` or `style` for genuine formatting/lint violations that do not affect functionality.

## Output Requirements

Return a JSON object with exactly this structure:

{
"comments": [
{
"title": "Short, specific description of the issue",
"description": "Detailed explanation of the problem and its impact",
"category": "bug | lint | security | performance | code_quality | maintainability | testing | documentation | style | other",
"severity": "critical | high | medium | low | info",
"file_path": "Path of the affected file",
"lines": "Affected line or line range, e.g. 42 or 42-48",
"suggestion": "Recommended fix",
"rationale": "Why this fix is appropriate",
"suggested_code": "Corrected code example or null"
}
]
}

Each comment must contain exactly these fields:

* `title`
* `description`
* `category`
* `severity`
* `file_path`
* `lines`
* `suggestion`
* `rationale`
* `suggested_code`

If there are no valid issues, return:

{
"comments": []
}

## Important Rules

* The output must contain valid JSON.
* Do not include Markdown fences.
* Do not include commentary outside the JSON object.
* Do not duplicate findings.
* Do not invent issues.
* Do not omit valid issues simply because only one specialized agent identified them.
* Prefer precise, actionable comments over vague recommendations.
* Base the final review on the actual file diff and the supplied agent findings.
* When multiple agents identify the same issue, produce one consolidated comment rather than multiple comments.
* The final output represents the review of the **single file being analyzed**, not a separate review for each specialized agent.

"""
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
