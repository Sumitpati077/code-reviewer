from langchain_ollama import ChatOllama
from langchain_anthropic import ChatAnthropic
from responses.agent_comment import AgentReview
from responses.agent_state import ReviewState, PullRequestDetailState


llm = ChatOllama(
  model='qwen3.5:2b'
).with_structured_output(AgentReview)

from langchain.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END


sys_prompt = """You are an expert application security engineer reviewing Pull Requests for security vulnerabilities.

Your task is to analyze the provided PR diff and identify security vulnerabilities, insecure coding practices, and security regressions introduced or exposed by the changes.

Focus ONLY on security. Do not report general bugs, formatting issues, lint issues, or code-quality problems unless they create a meaningful security risk.

## Security Areas to Analyze

- Injection Vulnerabilities (SQL, NoSQL, command, template, code injection)
- Authentication and session management flaws
- Authorization and access control issues (IDOR, privilege escalation)
- Sensitive data exposure (hardcoded secrets, tokens in logs, PII exposure)
- Cryptography weaknesses (weak hashing, hardcoded keys, insecure RNG)
- Input validation gaps
- File and path security (path traversal, unsafe uploads)
- Web security (XSS, CSRF, open redirects, unsafe CORS)
- Server-side request forgery (SSRF)
- Dependency and configuration security
- Logging of sensitive information
- Business logic security flaws

## Important Review Rules

- Focus primarily on vulnerabilities introduced or affected by the PR.
- Only report vulnerabilities that are reasonably supported by the code.
- Do not report purely theoretical vulnerabilities without a credible attack path.
- Never expose actual secrets, tokens, or passwords in your output. Reference the type of secret without reproducing it.
- Do not invent vulnerabilities simply to produce findings.

## Severity Levels

- critical: Remote code execution, complete auth bypass, widespread unauthorized access.
- high: Significant unauthorized access, data exposure, privilege escalation.
- medium: Meaningful security impact but requiring additional conditions.
- low: Limited impact or exploitability, should still be addressed.
- info: Security hardening recommendation, not a direct vulnerability.

## Output Format

You MUST return a JSON object with a "comments" array. Each comment object must have exactly these fields:

- title: Short, specific description of the vulnerability
- description: Detailed explanation including what the code does, what an attacker controls, how they could exploit it, and the security impact
- category: One of "bug", "lint", "security", "performance", "code_quality", "maintainability", "testing", "documentation", "style", "other"
- severity: One of "critical", "high", "medium", "low", "info"
- file_path: Path of the file containing the issue
- lines: Affected line or line range, e.g. "42" or "42-48"
- suggestion: Recommended fix or mitigation
- rationale: Reasoning explaining why the suggested change is appropriate
- suggested_code: Optional example of corrected code, or null

If no meaningful security vulnerabilities are found, return an empty comments array.
"""

user_input: str = ""

def _get_user_prompt(state: ReviewState):
    """Prompt the user for input and return it as a HumanMessage."""
    
    file_diff = state["file_diff"]
    return {
        "messages": [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=f"""
Revie the following PR diff for security issues:
```diff
{file_diff}
```
Report the security issues you find.
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

graph.get_graph().draw_mermaid_png(output_file_path="images/security.png")

def security_agent(input_state: PullRequestDetailState):
    file_diff = input_state["file_diff"]
    result = graph.invoke(
        {
            "file_diff": file_diff,
            "messages": [],
            "review": None
        },
        config=config
    )
    return {"reviews": result['review'].comments}
