import asyncio
import os
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()

async def main():
    email = os.getenv("JIRA_EMAIL")
    token = os.getenv("JIRA_API_TOKEN")
    url = os.getenv("JIRA_BASE_URL")

    # Env vars might not be needed for mcp-remote as it uses browser auth, 
    # but we'll keep them in the env just in case.
    if not email or not token or not url:
        print("Warning: JIRA_EMAIL, JIRA_API_TOKEN, or JIRA_BASE_URL not found in .env. Proceeding with mcp-remote which might use browser auth.")

    # Construct the npx command
    env = os.environ.copy()
    if email: env["JIRA_EMAIL"] = email
    if token: env["JIRA_API_TOKEN"] = token
    if url: env["JIRA_BASE_URL"] = url

    # Use the official Atlassian MCP remote endpoint
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "mcp-remote", "https://mcp.atlassian.com/v1/sse"],
        env=env
    )

    print("Starting Atlassian MCP server...")
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                print("Connected to MCP server!")
                
                # List available tools
                tools = await session.list_tools()
                tool_names = [t.name for t in tools.tools]
                print(f"\nAvailable tools: {tool_names}")

                # 1. Get Cloud ID
                print("\nFetching Cloud ID...")
                resources = await session.call_tool("getAccessibleAtlassianResources", arguments={})
                print(f"Resources: {resources}")
                
                # Parse cloudId from resources
                # The output format depends on the tool, but usually it returns a list of resources.
                # We'll assume the first one is the target or try to find the one matching the site URL.
                # For now, let's just print it and try to extract it if possible, 
                # or if the tool returns a direct list, we take the first 'id'.
                
                cloud_id = None
                if resources.content:
                    import json
                    try:
                        data = json.loads(resources.content[0].text)
                        if isinstance(data, list) and len(data) > 0:
                            cloud_id = data[0]['id']
                            print(f"Found Cloud ID: {cloud_id}")
                    except:
                        print("Could not parse Cloud ID from response, trying raw content...")
                        print(resources.content)

                if cloud_id:
                    # 2. Fetch KAN-6
                    print(f"\nFetching Jira Issue KAN-6...")
                    try:
                        issue = await session.call_tool("getJiraIssue", arguments={"issueIdOrKey": "KAN-6", "cloudId": cloud_id})
                        print("Issue Details:")
                        if issue.content:
                             print(issue.content[0].text)
                        else:
                             print(issue)
                    except Exception as e:
                        print(f"Error fetching issue: {e}")
                else:
                    print("Skipping issue fetch because Cloud ID could not be determined.")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
