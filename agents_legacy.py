import os
from google.adk import Agent
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import google.generativeai as genai
import json

# Configure Gemini
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

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

    def get_agent_card(self):
        return {
            "name": self.name,
            "description": self.description,
            "capabilities": ["fetch_jira_tickets"],
            "inputs": ["jira_status"],
            "outputs": ["tickets"]
        }

class CodeAnalyzer(Agent):
    def __init__(self, name="CodeAnalyzer"):
        super().__init__(name=name)
        self.description = "Analyzes the codebase to find impact of changes."
        self.model = genai.GenerativeModel("gemini-2.5-flash")

    def get_agent_card(self):
        return {
            "name": self.name,
            "description": self.description,
            "capabilities": ["analyze_code_impact"],
            "inputs": ["tickets", "repo_owner", "repo_name"],
            "outputs": ["impact_analysis"]
        }

    async def run(self, context):
        repo_owner = "akshay-mp"
        repo_name = "simple_production_rag"
        tickets = context.get("tickets", [])
        print(f"[{self.name}] Analyzing impact for {len(tickets)} tickets on {repo_owner}/{repo_name}...")
        
        impact_analysis = []
        
        # Connect to GitHub MCP to fetch code context
        env = os.environ.copy()
        token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
        if token:
            env["GITHUB_PERSONAL_ACCESS_TOKEN"] = token
            
        server_params = StdioServerParameters(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env=env
        )
        
        code_context = ""
        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # List files to get an idea of the structure
                    # Note: Tool names might vary, assuming 'list_directory' or similar exists, 
                    # but for safety in this demo we might try to search or just read README if possible.
                    # Let's try to search for python files or read README.
                    
                    # For this demo, let's try to read README.md
                    try:
                        # We need to know the tool name for reading files. Usually 'read_file'.
                        # We'll try to read README.md
                        result = await session.call_tool("get_file_contents", arguments={"owner": repo_owner, "repo": repo_name, "path": "README.md"})
                        if result.content:
                            code_context += f"README.md:\n{result.content[0].text[:1000]}\n\n"
                    except Exception as e:
                        print(f"[{self.name}] Could not read README: {e}")

        except Exception as e:
            print(f"[{self.name}] Error fetching code context: {e}")
            # Fallback
            code_context = "Could not fetch remote code. Assuming standard Python structure."

        for ticket in tickets:
            key = ticket.get('key')
            summary = ticket.get('fields', {}).get('summary', '')
            description = ticket.get('fields', {}).get('description', '')
            
            prompt = f"""
            Analyze the impact of this Jira ticket on the codebase {repo_owner}/{repo_name}.
            
            Ticket: {key} - {summary}
            Description: {description}
            
            Codebase Context:
            {code_context}
            
            Identify which files or components need to be changed.
            """
            
            response = self.model.generate_content(prompt)
            analysis = response.text
            impact_analysis.append({"ticket": key, "analysis": analysis})
            
        return {"impact_analysis": impact_analysis}

class GitHubExecutor(Agent):
    def __init__(self, name="GitHubExecutor"):
        super().__init__(name=name)
        self.description = "Interacts with GitHub to list or create issues."

    def get_agent_card(self):
        return {
            "name": self.name,
            "description": self.description,
            "capabilities": ["list_github_issues", "create_github_issues"],
            "inputs": ["action", "repo_owner", "repo_name", "impact_analysis"],
            "outputs": ["existing_issues", "created_issues"]
        }

    async def run(self, context):
        repo_owner = "akshay-mp"
        repo_name = "simple_production_rag"
        action = context.get("action", "create_issues") # Default to create for backward compatibility if needed
        
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
                            import json
                            try:
                                issues_data = json.loads(list_result.content[0].text)
                                # Return a list of dicts or just titles? Let's return full objects or simplified dicts
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
