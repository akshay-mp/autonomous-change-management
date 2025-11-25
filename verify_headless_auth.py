import os
import asyncio
from agents.jira_collector import JiraCollector
from agents.github_executor import GitHubExecutor

async def verify_headless():
    print("Verifying Headless Auth Logic...")
    
    # Mock Env Vars
    os.environ["ATLASSIAN_EMAIL"] = "mock_email@example.com"
    os.environ["ATLASSIAN_TOKEN"] = "mock_token"
    os.environ["ATLASSIAN_BASE_URL"] = "https://mock.atlassian.net"
    os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"] = "mock_pat"
    
    # Test Jira Collector
    print("\n--- Testing JiraCollector ---")
    jira = JiraCollector()
    # We expect this to fail connection but print "Fetching Jira tickets..." and use the env vars
    # Since we can't easily mock the stdio process without more complex code, we'll just run it 
    # and catch the expected exception or see the output.
    try:
        await jira.run({})
    except Exception as e:
        print(f"JiraCollector run finished with: {e}")
        
    # Test GitHub Executor
    print("\n--- Testing GitHubExecutor ---")
    github = GitHubExecutor()
    try:
        await github.run({"action": "list_issues"})
    except Exception as e:
        print(f"GitHubExecutor run finished with: {e}")

if __name__ == "__main__":
    asyncio.run(verify_headless())
