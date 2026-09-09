# Code Reviewer
This is a hobby project that I have been building to test my knowledge and learnings of the langchain and langgraph.

## Setup

### Prerequisites
- [uv](https://docs.astral.sh/uv/)
- git
- Python 3.14

### Clone the repository
Clone the repository using:
```bash
git clone git@github.com:Sumitpati077/code-reviewer.git
cd code-reviewer
```

### Install dependencies
Use uv to sync the project dependencies from the lockfile:
```bash
uv sync
```

### Configure environment variables
Copy the sample environment file and fill in the required values:
```bash
cp .env.sample .env
```
Then open `.env` and set `GITHUB_PAT` to a valid [GitHub Personal Access Token](https://github.com/settings/tokens) that has read access to the repository you want to review.

## Running the project
Run the main script with uv:
```bash
uv run main.py
```
