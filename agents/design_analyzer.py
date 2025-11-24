import os
import google.generativeai as genai
from google.adk import Agent
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Configure Gemini
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

class DesignAnalyzer(Agent):
    def __init__(self, name="DesignAnalyzer"):
        super().__init__(name=name)
        self.description = "Analyzes the current design and identifies component changes."
        self.model = genai.GenerativeModel("gemini-2.5-flash")

    async def run(self, context):
        repo_owner = "akshay-mp"
        repo_name = "simple_production_rag"
        tickets = context.get("tickets", [])
        print(f"[{self.name}] Analyzing design impact for {len(tickets)} tickets on {repo_owner}/{repo_name}...")
        
        design_analysis = []
        
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
                    
                    # Strategy:
                    # 1. Explore repo structure (root + likely folders) to find .md and .puml files.
                    # 2. Use LLM to select the most relevant design documents.
                    # 3. Read the selected documents.
                    
                    candidate_files = []
                    folders_to_check = ["", "docs", "specifications", "design", "architecture"]
                    checked_folders = set()
                    
                    print(f"[{self.name}] Exploring repository structure for design documents...")
                    
                    for folder in folders_to_check:
                        if folder in checked_folders:
                            continue
                        checked_folders.add(folder)
                        
                        try:
                            # Adjust path for root
                            path_arg = folder if folder else "."
                            # Note: list_directory behavior might vary, assuming it returns list of entries
                            entries = await session.call_tool("list_directory", arguments={"owner": repo_owner, "repo": repo_name, "path": path_arg})
                            
                            if entries.content:
                                # Parse entries - assuming text output or JSON-like structure in content
                                # We'll do a simple text parsing if it's a string representation, 
                                # or iterate if it's a list. The MCP client usually returns a list of Content objects.
                                # Let's assume the text content lists files.
                                # For robustness, we'll assume we can get filenames.
                                # If the tool returns a JSON string, we parse it. 
                                # If it returns plain text lines, we split.
                                
                                text_content = entries.content[0].text
                                lines = text_content.splitlines()
                                
                                for line in lines:
                                    # Simple heuristic to extract filename from ls-like output
                                    # This depends heavily on the tool output format.
                                    # Let's assume the tool returns just filenames or "type name"
                                    cleaned_line = line.strip()
                                    if not cleaned_line: continue
                                    
                                    # If line contains directory info, add to folders_to_check if relevant
                                    # For now, let's just look for extensions in the line
                                    if ".md" in cleaned_line or ".puml" in cleaned_line:
                                        # Construct full path
                                        # This is a bit hacky without structured output, but works for many ls outputs
                                        # We'll try to extract the last word as filename if it looks like a file
                                        parts = cleaned_line.split()
                                        filename = parts[-1] 
                                        if filename.endswith(".md") or filename.endswith(".puml"):
                                            full_path = f"{folder}/{filename}" if folder else filename
                                            candidate_files.append(full_path)
                                            
                        except Exception as e:
                            # print(f"[{self.name}] Error listing {folder}: {e}")
                            pass

                    print(f"[{self.name}] Found candidate design files: {candidate_files}")
                    
                    selected_files = []
                    if candidate_files:
                        # Ask LLM to select relevant files
                        selection_prompt = f"""
                        I have found the following files in the repository that might contain design documentation:
                        {json.dumps(candidate_files)}
                        
                        Which of these files are most likely to contain the high-level system design, architecture, or component diagrams?
                        Select up to 3 most relevant files.
                        Return ONLY a JSON list of the selected file paths.
                        """
                        try:
                            response = self.model.generate_content(selection_prompt)
                            text = response.text.strip()
                            if text.startswith("```json"): text = text[7:]
                            if text.endswith("```"): text = text[:-3]
                            selected_files = json.loads(text)
                            print(f"[{self.name}] LLM selected design files: {selected_files}")
                        except Exception as e:
                            print(f"[{self.name}] LLM selection failed: {e}. Defaulting to all candidates.")
                            selected_files = candidate_files[:3] # Limit to 3
                    else:
                        # Fallback if discovery failed
                        selected_files = ["README.md"]

                    # Read selected files
                    for file_path in selected_files:
                        try:
                            result = await session.call_tool("get_file_contents", arguments={"owner": repo_owner, "repo": repo_name, "path": file_path})
                            if result.content:
                                code_context += f"File: {file_path}\nContent:\n{result.content[0].text[:3000]}\n\n"
                        except Exception as e:
                            print(f"[{self.name}] Could not read {file_path}: {e}")


        except Exception as e:
            print(f"[{self.name}] Error fetching code context: {e}")
            # Fallback
            code_context = "Could not fetch remote code. Assuming standard Python structure."

        for ticket in tickets:
            key = ticket.get('key')
            summary = ticket.get('fields', {}).get('summary', '')
            description = ticket.get('fields', {}).get('description', '')
            
            prompt = f"""
            Analyze the design impact of this Jira ticket on the codebase {repo_owner}/{repo_name}.
            
            Ticket: {key} - {summary}
            Description: {description}
            
            Current Design Context (from README):
            {code_context}
            
            Task:
            1. Identify the current design architecture based on the context.
            2. List specific components that need changes.
            3. List specific components that need to be redesigned or created.
            
            Output Format:
            **Current Design**: <summary>
            **Components to Change**: <list>
            **Components to Redesign/Create**: <list>
            """
            
            response = self.model.generate_content(prompt)
            analysis = response.text
            design_analysis.append({"ticket": key, "analysis": analysis})
            
        return {"design_analysis": design_analysis}
