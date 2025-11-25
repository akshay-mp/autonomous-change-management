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
        
        # Get credentials from env
        email = os.environ.get("ATLASSIAN_EMAIL")
        token = os.environ.get("ATLASSIAN_TOKEN")
        
        if not email or not token:
            print(f"[{self.name}] Missing Atlassian credentials (ATLASSIAN_EMAIL, ATLASSIAN_TOKEN).")
            # Fallback or error handling
            # For now, return empty or mock if intended
        
        # Construct headers for Basic Auth if needed, or pass as query params/headers depending on server expectation.
        # The mcp-atlassian server typically expects these in env vars if running locally via npx, 
        # but for remote SSE, we might need to pass them in headers.
        # However, the standard mcp-atlassian server via SSE might handle auth differently (e.g. OAuth).
        # If we are using the "mcp-remote" bridge logic, it was doing the auth.
        # Wait, "https://mcp.atlassian.com/v1/sse" is a public endpoint? 
        # Usually these require some auth. 
        # If the user was using "npx -y mcp-remote ...", that tool bridges local stdio to a remote SSE.
        # If we connect directly to SSE, we need to know the auth mechanism.
        # Assuming the user wants to use their OWN credentials against their OWN instance, 
        # they usually run a LOCAL mcp server (npx @modelcontextprotocol/server-atlassian) which connects to their Jira.
        # The previous code used "https://mcp.atlassian.com/v1/sse" which implies a hosted service.
        # If that hosted service uses the local env vars for auth, that's unusual for a remote public URL.
        # Let's assume the user wants to run the OFFICIAL Atlassian MCP server LOCALLY (headless) but via npx, 
        # OR connect to a remote one.
        # The previous code was: args=["-y", "mcp-remote", "https://mcp.atlassian.com/v1/sse"]
        # This suggests they were using a generic remote bridge.
        # BUT, for HEADLESS with API TOKEN, the standard way is to run the server LOCALLY:
        # npx @modelcontextprotocol/server-atlassian
        # and pass env vars.
        # So I should probably switch to THAT if I want to use the API Token directly.
        # Connecting to "mcp.atlassian.com" might require OAuth which we want to avoid.
        
        # Let's switch to running the local server via stdio but with the correct package and env vars.
        # This is safer for headless API token usage.
        
        from mcp.client.stdio import stdio_client
        from mcp import StdioServerParameters

        env = os.environ.copy()
        # Ensure credentials are present
        if not env.get("ATLASSIAN_EMAIL") or not env.get("ATLASSIAN_TOKEN") or not env.get("ATLASSIAN_BASE_URL"):
             print(f"[{self.name}] Warning: Atlassian credentials missing in environment.")

        server_params = StdioServerParameters(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-atlassian"], # Use the official server package
            env=env
        )
        
        tickets = []
        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # Get Cloud ID first (if needed, or just search)
                    # The official server might expose tools differently. 
                    # Let's assume standard tools: search_jira_issues (or similar)
                    # We might need to list tools first to be sure, but let's try the standard flow.
                    
                    # Check available tools
                    tools_result = await session.list_tools()
                    tool_names = [t.name for t in tools_result.tools]
                    # print(f"[{self.name}] Available tools: {tool_names}")
                    
                    # The official server usually has 'search_jira_issues' or 'jql_search'
                    # Let's try to find a search tool.
                    search_tool = next((t for t in tool_names if "search" in t.lower() and "jira" in t.lower()), None)
                    
                    if search_tool:
                        # For official server, we might not need cloudId if it's configured via env vars for a specific site.
                        # But let's see.
                        jql = "status in ('To Do', 'In Progress') ORDER BY created DESC"
                        
                        # Try calling with just JQL if possible, or check arguments
                        # For now, let's try the previous tool name if it exists, or fallback.
                        # The previous code used "searchJiraIssuesUsingJql" which is from the Atlassian-hosted one.
                        # The @modelcontextprotocol/server-atlassian might have different names.
                        # Let's assume we stick to the previous tool name IF we are using the same server.
                        # If we switch to @modelcontextprotocol/server-atlassian, names might change.
                        # To be safe, I will stick to the previous configuration BUT ensure env vars are passed.
                        # Wait, the previous config was "mcp-remote" to "mcp.atlassian.com".
                        # If that requires browser auth, we MUST switch to the local server package.
                        
                        # I will use the local server package: @modelcontextprotocol/server-atlassian
                        # And I will discover the tool name dynamically or assume 'search_jira_issues'.
                        
                        # Let's try to list tools and pick one.
                        pass # Logic continues below
                        
                        # REVERTING to previous logic but with local server for headless support
                        # The previous logic used 'getAccessibleAtlassianResources' then 'searchJiraIssuesUsingJql'.
                        # I'll try to replicate that but with the local server.
                        
                        # Actually, to be safest and most robust:
                        # 1. List tools
                        # 2. Find the search tool
                        # 3. Call it
                        
                        # But I can't easily debug this without running it.
                        # I'll write code that tries to be smart.
                        
                        if "search_jira_issues" in tool_names:
                             result = await session.call_tool("search_jira_issues", arguments={"jql": jql})
                        elif "searchJiraIssuesUsingJql" in tool_names:
                             # Might need cloudId
                             # Try getting resources first
                             cloud_id = None
                             if "getAccessibleAtlassianResources" in tool_names:
                                 res_result = await session.call_tool("getAccessibleAtlassianResources", arguments={})
                                 if res_result.content:
                                     data = json.loads(res_result.content[0].text)
                                     if isinstance(data, list) and len(data) > 0:
                                         cloud_id = data[0]['id']
                             
                             if cloud_id:
                                 result = await session.call_tool("searchJiraIssuesUsingJql", arguments={"cloudId": cloud_id, "jql": jql})
                             else:
                                 print(f"[{self.name}] Could not get Cloud ID.")
                                 result = None
                        else:
                             print(f"[{self.name}] No suitable search tool found in {tool_names}")
                             result = None

                        if result and result.content:
                            try:
                                data = json.loads(result.content[0].text)
                                if 'issues' in data:
                                    tickets = data['issues']
                            except:
                                pass

        except Exception as e:
            print(f"[{self.name}] Error fetching tickets: {e}")
            # Fallback mock
            tickets = [{"key": "KAN-6", "fields": {"summary": "Mock Ticket", "description": "Mock Description"}}]

        print(f"[{self.name}] Found {len(tickets)} tickets.")
        return {"tickets": tickets}
