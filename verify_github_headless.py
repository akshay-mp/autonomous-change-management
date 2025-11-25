import os
import asyncio
from dotenv import load_dotenv
from agents.github_executor import GitHubExecutor

async def verify_github_headless():
    load_dotenv()
    
    print("Verifying GitHub Headless Auth...")
    print(f"GITHUB_PERSONAL_ACCESS_TOKEN present: {bool(os.environ.get('GITHUB_PERSONAL_ACCESS_TOKEN'))}")
    
    github = GitHubExecutor()
    
    # Test listing issues
    print("\n--- Testing List Issues ---")
    try:
        result = await github.run({"action": "list_issues"})
        existing_issues = result.get("existing_issues", [])
        print(f"✓ Successfully listed {len(existing_issues)} issues")
        if existing_issues:
            print(f"  Sample: {existing_issues[0]}")
    except Exception as e:
        print(f"✗ Failed to list issues: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify_github_headless())
