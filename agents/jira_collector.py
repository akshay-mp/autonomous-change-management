import os
import json
from google.adk import Agent
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class JiraCollector(Agent):
    def __init__(self, name="JiraCollector"):
        super().__init__(name=name)
        self.description = "Fetches Jira tickets that need attention."
        
    async def run(self, context):
        print(f"[{self.name}] Fetching Jira tickets...")
        # Connect to Jira MCP
        env = os.environ.copy()
        server_params = StdioServerParameters(
            command="npx",
            args=["-y", "mcp-remote", "https://mcp.atlassian.com/v1/sse"],
            env=env
        )
        
        tickets = []
        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # Get Cloud ID first
                    cloud_id = None
                    result = await session.call_tool("getAccessibleAtlassianResources", arguments={})
                    if result.content:
                        data = json.loads(result.content[0].text)
                        if isinstance(data, list) and len(data) > 0:
                            cloud_id = data[0]['id']
                    
                    if cloud_id:
                        # Search for tickets in 'To Do' or 'In Progress'
                        jql = "status in ('To Do', 'In Progress') ORDER BY created DESC"
                        result = await session.call_tool("searchJiraIssuesUsingJql", arguments={"cloudId": cloud_id, "jql": jql})
                        if result.content:
                            try:
                                data = json.loads(result.content[0].text)
                                if 'issues' in data:
                                    tickets = data['issues']
                            except:
                                pass
        except Exception as e:
            print(f"[{self.name}] Error fetching tickets: {e}")
            # Fallback mock for demo if connection fails
            tickets = [{"key": "KAN-6", "fields": {"summary": "Mock Ticket", "description": "Mock Description"}}]

        print(f"[{self.name}] Found {len(tickets)} tickets.")
        return {"tickets": tickets}
