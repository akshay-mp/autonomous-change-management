import asyncio
import os
from dotenv import load_dotenv
from agents.jira_collector import JiraCollector

async def test_jira_collector():
    """Test the JiraCollector agent to verify Jira API connectivity."""
    
    # Load environment variables
    load_dotenv()
    
    print("=" * 60)
    print("Testing JiraCollector Agent")
    print("=" * 60)
    
    # Check if credentials are set
    email = os.getenv("JIRA_EMAIL")
    token = os.getenv("JIRA_API_TOKEN")
    base_url = os.getenv("JIRA_BASE_URL")
    
    print(f"\nEnvironment Variables:")
    print(f"  JIRA_EMAIL: {'✓ Set' if email else '✗ Missing'}")
    print(f"  JIRA_API_TOKEN: {'✓ Set' if token else '✗ Missing'}")
    print(f"  JIRA_BASE_URL: {base_url if base_url else '✗ Missing'}")
    print()
    
    # Create and run the agent
    collector = JiraCollector()
    
    print(f"Running {collector.name}...")
    print("-" * 60)
    
    try:
        result = await collector.run(context={})
        
        print("\n" + "=" * 60)
        print("Results:")
        print("=" * 60)
        
        tickets = result.get("tickets", [])
        print(f"\nTotal tickets fetched: {len(tickets)}\n")
        
        if tickets:
            print("Sample tickets:")
            for i, ticket in enumerate(tickets[:5], 1):  # Show first 5 tickets
                key = ticket.get("key", "N/A")
                fields = ticket.get("fields", {})
                summary = fields.get("summary", "N/A")
                status = fields.get("status", {})
                status_name = status.get("name", "N/A") if isinstance(status, dict) else "N/A"
                
                print(f"\n  {i}. [{key}] {summary}")
                print(f"     Status: {status_name}")
        else:
            print("No tickets found or using mock data.")
        
        print("\n" + "=" * 60)
        print("✓ Test completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"✗ Error during test: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_jira_collector())
