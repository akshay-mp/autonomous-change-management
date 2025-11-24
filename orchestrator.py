import os
import json
import glob
import google.generativeai as genai
from google.adk import Agent

# Import agents
from agents.jira_collector import JiraCollector
from agents.design_analyzer import DesignAnalyzer
from agents.github_executor import GitHubExecutor

# Configure Gemini
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

class AgentRegistry:
    def __init__(self):
        self.agents = {}
        self.manifests = {}
        self._load_agents()

    def _load_agents(self):
        # Instantiate agents
        # In a real system, this could be dynamic import based on manifest
        self.agents["JiraCollector"] = JiraCollector()
        self.agents["DesignAnalyzer"] = DesignAnalyzer()
        self.agents["GitHubExecutor"] = GitHubExecutor()

        # Load manifests
        manifest_files = glob.glob("manifests/*.json")
        for mf in manifest_files:
            try:
                with open(mf, "r") as f:
                    manifest = json.load(f)
                    self.manifests[manifest["name"]] = manifest
            except Exception as e:
                print(f"Error loading manifest {mf}: {e}")

    def get_agent(self, name):
        return self.agents.get(name)

    def get_all_manifests(self):
        return list(self.manifests.values())

    def get_agent_for_capability(self, capability):
        for name, manifest in self.manifests.items():
            if capability in manifest.get("capabilities", []):
                return self.agents.get(name)
        return None

class ChangeManagementOrchestrator(Agent):
    def __init__(self, name="ChangeManagementOrchestrator"):
        super().__init__(name=name)

    async def run(self, context={}):
        memory_file = "orchestrator_memory.json"
        print(f"[{self.name}] Starting A2A dynamic orchestration...")
        
        # Initialize components here to avoid Pydantic field issues
        registry = AgentRegistry()
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        # 1. Discovery
        manifests = registry.get_all_manifests()
        capabilities = []
        for m in manifests:
            capabilities.extend(m.get("capabilities", []))
        
        print(f"[{self.name}] Discovered capabilities: {capabilities}")

        # 2. Planning
        goal = "Fetch Jira tickets, check against existing GitHub issues to avoid duplicates, analyze design impact for new tickets, and create GitHub issues."
        
        # Load memory
        memory = self._load_memory(memory_file)
        
        plan = self._generate_plan(goal, manifests, model, memory)
        print(f"[{self.name}] Generated Plan: {json.dumps(plan, indent=2)}")

        # 3. Execution
        execution_log = []
        success = True
        
        for step in plan:
            agent_name = step.get("agent")
            capability = step.get("capability")
            reasoning = step.get("reasoning")
            
            print(f"[{self.name}] Executing Step: {capability} ({reasoning})")
            
            agent = registry.get_agent(agent_name)
            if not agent:
                print(f"[{self.name}] Agent {agent_name} not found. Skipping.")
                success = False
                execution_log.append({"step": step, "status": "failed", "error": "Agent not found"})
                continue

            # Prepare context for the agent
            # Special handling for GitHubExecutor which needs 'action'
            if agent_name == "GitHubExecutor":
                if "list" in capability:
                    context["action"] = "list_issues"
                elif "create" in capability:
                    context["action"] = "create_issues"
                    # Map design_analysis to impact_analysis for backward compatibility if needed, 
                    # or update GitHubExecutor to handle design_analysis.
                    # For now, let's assume GitHubExecutor expects 'impact_analysis' key, 
                    # so we might need to map it if DesignAnalyzer returns 'design_analysis'.
                    if "design_analysis" in context:
                        context["impact_analysis"] = context["design_analysis"]

            try:
                # Execute
                result = await agent.run(context)
                context.update(result)
                execution_log.append({"step": step, "status": "success"})

                # Post-processing for optimization (Duplicate Filtering)
                if capability == "list_github_issues" and "tickets" in context:
                    self._filter_duplicates(context)
            except Exception as e:
                print(f"[{self.name}] Step failed: {e}")
                success = False
                execution_log.append({"step": step, "status": "failed", "error": str(e)})

        # Save memory
        self._save_memory(memory_file, goal, plan, success, execution_log)

        print(f"[{self.name}] Orchestration complete.")
        return context

    def _load_memory(self, memory_file):
        if os.path.exists(memory_file):
            try:
                with open(memory_file, "r") as f:
                    return json.load(f)
            except:
                pass
        return []

    def _save_memory(self, memory_file, goal, plan, success, log):
        memory = self._load_memory(memory_file)
        entry = {
            "goal": goal,
            "plan": plan,
            "success": success,
            "log": log,
            # "timestamp": datetime.now().isoformat() # Requires import datetime
        }
        memory.append(entry)
        # Keep only last 10 entries
        if len(memory) > 10:
            memory = memory[-10:]
            
        try:
            with open(memory_file, "w") as f:
                json.dump(memory, f, indent=2)
        except Exception as e:
            print(f"[{self.name}] Failed to save memory: {e}")

    def _generate_plan(self, goal, manifests, model, memory):
        # Prompt Gemini to generate a plan
        manifest_str = json.dumps(manifests, indent=2)
        
        # Format memory for context
        memory_context = ""
        if memory:
            successful_plans = [m["plan"] for m in memory if m["success"]]
            if successful_plans:
                memory_context = f"\nHere are examples of successful plans from the past:\n{json.dumps(successful_plans[:2], indent=2)}\n"
        
        prompt = f"""
        You are an autonomous orchestrator.
        Goal: {goal}
        
        Available Agents and Capabilities:
        {manifest_str}
        
        {memory_context}
        
        Create a JSON execution plan. The plan should be a list of steps.
        Each step must have:
        - "agent": Name of the agent
        - "capability": The capability to use
        - "reasoning": Brief reason for this step
        
        Order the steps logically to achieve the goal efficiently.
        IMPORTANT: To avoid duplicates, we must list existing issues BEFORE creating new ones.
        
        Return ONLY the JSON list.
        """
        
        try:
            response = model.generate_content(prompt)
            text = response.text.strip()
            # Clean up markdown code blocks if present
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            return json.loads(text)
        except Exception as e:
            print(f"[{self.name}] Planning failed: {e}. Fallback to hardcoded plan.")
            return [
                {"agent": "JiraCollector", "capability": "fetch_jira_tickets", "reasoning": "Get new work"},
                {"agent": "GitHubExecutor", "capability": "list_github_issues", "reasoning": "Check existing work"},
                {"agent": "DesignAnalyzer", "capability": "analyze_design_impact", "reasoning": "Analyze design"},
                {"agent": "GitHubExecutor", "capability": "create_github_issues", "reasoning": "Create tasks"}
            ]

    def _filter_duplicates(self, context):
        tickets = context.get("tickets", [])
        existing_issues = context.get("existing_issues", [])
        existing_titles = [issue.get("title", "") for issue in existing_issues]
        
        print(f"[{self.name}] Filtering {len(tickets)} tickets against {len(existing_issues)} existing issues...")
        new_tickets = []
        for ticket in tickets:
            key = ticket.get('key')
            # Assuming a naming convention for issues
            expected_title = f"Implement changes for {key}"
            
            # Check if any existing issue title contains the key or matches the expected title
            is_duplicate = False
            for title in existing_titles:
                if key in title:
                    is_duplicate = True
                    break
            
            if is_duplicate:
                print(f"[{self.name}] Skipping {key} (Already exists)")
            else:
                new_tickets.append(ticket)
        
        context["tickets"] = new_tickets
        print(f"[{self.name}] {len(new_tickets)} new tickets to process.")
