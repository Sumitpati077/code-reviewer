from pydantic import BaseModel, Field
from typing import Literal

class AgentComment(BaseModel):
    """A review finding produced by a code-review sub-agent."""

    title: str = Field(
        description="Short, concise title describing the issue."
    )

    description: str = Field(
        description="Detailed explanation of the issue and why it matters."
    )

    category: Literal[
        "bug",
        "lint",
        "security",
        "performance",
        "code_quality",
        "maintainability",
        "testing",
        "documentation",
        "style",
        "other",
    ] = Field(
        description="Category of the review finding."
    )

    severity: Literal[
        "critical",
        "high",
        "medium",
        "low",
        "info",
    ] = Field(
        description="Severity of the finding."
    )

    file_path: str = Field(
        description="Path of the file containing the issue."
    )

    lines: str = Field(
        description="Affected line or line range, for example '42' or '42-48'."
    )

    suggestion: str = Field(
        description="Recommended fix or improvement."
    )

    rationale: str = Field(
        description="Reasoning explaining why the suggested change is appropriate."
    )
    suggested_code: str | None = Field(
        default=None,
        description="Optional example of corrected code."
    )
    
class AgentReview(BaseModel):
    comments: list[AgentComment] = Field(
        default_factory=list,
        description="Review findings discovered by the agent."
    )
