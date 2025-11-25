import os
import json
import base64
import aiohttp
from google.adk import Agent

class JiraCollector(Agent):
    def __init__(self, name="JiraCollector"):
        super().__init__(name=name)
        self.description = "Fetches Jira tickets that need attention."
        
    async def run(self, context):
        print(f"[{self.name}] Fetching Jira tickets...")
        
        # Get credentials from env
        email = os.environ.get("JIRA_EMAIL")
        token = os.environ.get("JIRA_API_TOKEN")
        base_url = os.environ.get("JIRA_BASE_URL")
        
        if not email or not token or not base_url:
            print(f"[{self.name}] Missing Jira credentials (JIRA_EMAIL, JIRA_API_TOKEN, JIRA_BASE_URL).")
            print(f"[{self.name}] Using mock data instead.")
            tickets = [{"key": "KAN-6", "fields": {"summary": "Mock Ticket", "description": "Mock Description"}}]
            return {"tickets": tickets}
        
        # Use Jira REST API directly (works in headless HF Spaces)
        tickets = []
        try:
            # Create Basic Auth header
            auth_string = f"{email}:{token}"
            auth_bytes = auth_string.encode('ascii')
            base64_bytes = base64.b64encode(auth_bytes)
            base64_auth = base64_bytes.decode('ascii')
            
            headers = {
                "Authorization": f"Basic {base64_auth}",
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            
            # JQL query for open tickets
            jql = "status in ('To Do', 'In Progress') ORDER BY created DESC"
            
            # Construct API URL (using new endpoint as per CHANGE-2046)
            api_url = f"{base_url}/rest/api/3/search/jql"
            params = {
                "jql": jql,
                "maxResults": 50,
                "fields": "summary,description,status,issuetype,priority,created"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        tickets = data.get('issues', [])
                        print(f"[{self.name}] Successfully fetched {len(tickets)} tickets from Jira API")
                    else:
                        error_text = await response.text()
                        print(f"[{self.name}] Jira API error {response.status}: {error_text}")
                        # Fallback to mock
                        tickets = [{"key": "KAN-6", "fields": {"summary": "Mock Ticket", "description": "Mock Description"}}]
                        
        except Exception as e:
            print(f"[{self.name}] Error fetching tickets: {e}")
            # Fallback mock
            tickets = [{"key": "KAN-6", "fields": {"summary": "Mock Ticket", "description": "Mock Description"}}]

        print(f"[{self.name}] Found {len(tickets)} tickets.")
        return {"tickets": tickets}
