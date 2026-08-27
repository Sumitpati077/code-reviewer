import os
import dotenv

dotenv.load_dotenv()
from services.github import fetch_pr, fetch_pr_diff



def main():
    pr = fetch_pr("Sumitpati077/node_project",7)
    for file in fetch_pr_diff(pr):
        print(file.filename)
        print(file.status)
        print(file.additions)
        print(file.deletions)
        print(file.changes)
        print(file.patch)

 
if __name__ == "__main__":
    main()
