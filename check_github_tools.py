import asyncio
import os
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()

async def main():
    print("Connecting to GitHub MCP...")
    env = os.environ.copy()
    token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    if token:
        env["GITHUB_PERSONAL_ACCESS_TOKEN"] = token
        
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-github"],
        env=env
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("Available Tools:")
            for tool in tools.tools:
                print(f"- {tool.name}")

if __name__ == "__main__":
    asyncio.run(main())
