import os
import json
from google.adk import Agent
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class GitHubExecutor(Agent):
    def __init__(self, name="GitHubExecutor"):
        super().__init__(name=name)
        self.description = "Interacts with GitHub to list or create issues."

    async def run(self, context):
        repo_owner = "akshay-mp"
        repo_name = "simple_production_rag"
        action = context.get("action", "create_issues") 
        
        # Connect to GitHub MCP
        env = os.environ.copy()
        token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
        if token:
            env["GITHUB_PERSONAL_ACCESS_TOKEN"] = token
            
        server_params = StdioServerParameters(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env=env
        )
        
        if action == "list_issues":
            print(f"[{self.name}] Listing issues from {repo_owner}/{repo_name}...")
            existing_issues = []
            try:
                async with stdio_client(server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        list_result = await session.call_tool("list_issues", arguments={
                            "owner": repo_owner, 
                            "repo": repo_name,
                            "state": "all"
                        })
                        if list_result.content:
                            try:
                                issues_data = json.loads(list_result.content[0].text)
                                existing_issues = [{"title": issue.get('title', ''), "number": issue.get('number')} for issue in issues_data]
                            except json.JSONDecodeError:
                                print(f"[{self.name}] Could not parse list_issues output as JSON.")
            except Exception as e:
                print(f"[{self.name}] Failed to list issues: {e}")
            return {"existing_issues": existing_issues}

        elif action == "create_issues":
            analysis_list = context.get("impact_analysis", [])
            print(f"[{self.name}] Creating issues in {repo_owner}/{repo_name} for {len(analysis_list)} items...")
            created_issues = []
            
            try:
                async with stdio_client(server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        
                        for item in analysis_list:
                            ticket = item['ticket']
                            analysis = item['analysis']
                            
                            title = f"Implement changes for {ticket}"
                            body = f"**Impact Analysis**\n\n{analysis}\n\nRef: {ticket}"
                            
                            try:
                                await session.call_tool("create_issue", arguments={
                                    "owner": repo_owner, 
                                    "repo": repo_name, 
                                    "title": title, 
                                    "body": body
                                })
                                created_issues.append(f"Created issue for {ticket} in {repo_owner}/{repo_name}")
                            except Exception as e:
                                print(f"[{self.name}] Failed to create issue for {ticket}: {e}")
                                created_issues.append(f"Failed to create issue for {ticket}")
                                
            except Exception as e:
                print(f"[{self.name}] Error updating GitHub: {e}")
                created_issues.append("Error connecting to GitHub")
                        
            return {"created_issues": created_issues}
        
        return {}
