import os
import dotenv

dotenv.load_dotenv()

from github import Auth, Github, Repository, PullRequest, PaginatedList, File

def _initialize_client() -> Github:
    """Create an authenticated GitHub client from GITHUB_PAT."""
    pat = os.getenv("GITHUB_PAT")
    if not pat:
        raise ValueError("GITHUB_PAT is missing")
    return Github(auth=Auth.Token(pat))

def _repository(client: Github, repo_name: str) -> Repository:
    return client.get_repo(repo_name)

def fetch_pr(repo: str, pr_number: int) -> PullRequest: 
    client = _initialize_client()
    repo = _repository(client=client, repo_name=repo)
    return repo.get_pull(pr_number)

def fetch_pr_diff(pr: PullRequest) -> PaginatedList[File]:
    return pr.get_files()
