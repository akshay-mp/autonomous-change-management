import asyncio
import os
from dotenv import load_dotenv
from orchestrator import ChangeManagementOrchestrator

load_dotenv()

async def main():
    print("Initializing Orchestrator...")
    orchestrator = ChangeManagementOrchestrator()
    
    print("Running Orchestrator...")
    context = await orchestrator.run()
    
    print("\n--- Execution Result ---")
    tickets = context.get("tickets", [])
    print(f"Tickets Found: {len(tickets)}")
    
    # Check for design analysis
    impacts = context.get("design_analysis", [])
    if not impacts:
        impacts = context.get("impact_analysis", [])
        
    print(f"Design/Impact Analysis Items: {len(impacts)}")
    
    issues = context.get("created_issues", [])
    print(f"Issues Created: {len(issues)}")
    
    if issues:
        print("Created Issues:")
        for issue in issues:
            print(f" - {issue}")

if __name__ == "__main__":
    asyncio.run(main())
