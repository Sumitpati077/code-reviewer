import os
import dotenv

dotenv.load_dotenv()
from services.github import fetch_pr, fetch_pr_diff



def main():
    from graphs.lint import lint_agent
    from graphs.bug_finder import bug_finder_agent
    from graphs.security import security_agent
    pr = fetch_pr("Sumitpati077/node_project",7)
    for index, file in enumerate(fetch_pr_diff(pr)):
        if index == 0:
            lint_agent(file.patch)
            bug_finder_agent(file.patch)
            security_agent(file.patch)

 
if __name__ == "__main__":
    main()
