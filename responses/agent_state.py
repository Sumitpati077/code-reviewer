from langgraph.graph import MessagesState

from responses.agent_comment import AgentReview

class ReviewState(MessagesState):
    file_diff: str
    review: AgentReview | None = None