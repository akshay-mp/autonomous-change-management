import asyncio
import os
from dotenv import load_dotenv
from orchestrator import ChangeManagementOrchestrator

load_dotenv()

async def main():
    print("Instantiating Orchestrator...")
    try:
        orchestrator = ChangeManagementOrchestrator()
        print("Orchestrator instantiated.")
        
        print("Running Orchestrator...")
        # We can pass a mock context if needed, but defaults should work
        result = await orchestrator.run()
        print("Orchestrator run complete.")
        print("Result:", result)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
