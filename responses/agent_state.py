import operator
from typing import Annotated, List
from typing_extensions import TypedDict

from langgraph.graph import MessagesState

from responses.agent_comment import AgentReview, AgentComment

class ReviewState(MessagesState):
    file_diff: str
    review: AgentReview | None = None


class PullRequestDetailState(TypedDict):
    """Input on the details of the pull request"""
    file_name: str
    file_diff: str
    reviews: Annotated[List[AgentComment], operator.add]
