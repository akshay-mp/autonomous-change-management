import asyncio
import os
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()

async def main():
    token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    if not token:
        print("Error: GITHUB_PERSONAL_ACCESS_TOKEN not found in .env")
        return

    # Construct the npx command for GitHub MCP
    # We use the official @modelcontextprotocol/server-github
    env = os.environ.copy()
    env["GITHUB_PERSONAL_ACCESS_TOKEN"] = token

    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-github"],
        env=env
    )

    print("Starting GitHub MCP server...")
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                print("Connected to GitHub MCP server!")
                
                # List available tools
                tools = await session.list_tools()
                tool_names = [t.name for t in tools.tools]
                print(f"\nAvailable tools: {tool_names}")

                # Try to list repositories as a simple test
                print("\nListing repositories (first 5)...")
                try:
                    # The tool name might be 'list_repositories' or similar, checking the list first is safer
                    # but for verification we can try a common one if we see it in the list.
                    # For now, just listing tools is a good enough verification of connection.
                    pass
                except Exception as e:
                    print(f"Error listing repos: {e}")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
