import os
import google.generativeai as genai
from google.adk import Agent
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Configure Gemini
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

class CodeAnalyzer(Agent):
    def __init__(self, name="CodeAnalyzer"):
        super().__init__(name=name)
        self.description = "Analyzes the codebase to find impact of changes."
        self.model = genai.GenerativeModel("gemini-2.5-flash")

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
                    
                    # For this demo, let's try to read README.md
                    try:
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
