import os
import gradio as gr
from dotenv import load_dotenv

load_dotenv()

def test_atlassian_mcp():
    print("Testing Gradio MCP Client with Atlassian...")
    try:
        # Attempt to load the Atlassian MCP server tools directly via SSE
        # Note: This requires the server to be accessible. 
        # The URL https://mcp.atlassian.com/v1/sse is the one used in the original code.
        # We need to pass auth headers or env vars. 
        # Gradio's load_tool might not support passing custom headers for SSE easily if it's just a URL.
        # But let's check if it picks up env vars.
        
        # Try gr.load with src="mcp"
        tool = gr.load("https://mcp.atlassian.com/v1/sse", src="mcp")
        print("Successfully loaded Atlassian tool via Gradio!")
        print(tool)
    except Exception as e:
        print(f"Failed to load Atlassian tool: {e}")

if __name__ == "__main__":
    print(f"Gradio Version: {gr.__version__}")
    print(dir(gr)) # Uncomment if needed to see all attributes
    test_atlassian_mcp()
