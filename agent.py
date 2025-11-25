import gradio as gr
import os
import asyncio
from dotenv import load_dotenv
from orchestrator import ChangeManagementOrchestrator

load_dotenv()

async def run_analysis():
    orchestrator = ChangeManagementOrchestrator()
    
    # We can yield progress updates here if we modify the orchestrator to yield
    # For now, we'll just run it and return the final result
    
    results = []
    yield gr.update(value="Starting Analysis...", visible=True)
    
    try:
        # Run the orchestrator
        # Note: In a real app, we'd want to stream logs from the agents
        final_context = await orchestrator.run()
        
        # Format output
        tickets = final_context.get("tickets", [])
        impacts = final_context.get("impact_analysis", [])
        issues = final_context.get("created_issues", [])
        
        output_md = f"""
        ## Analysis Complete
        
        ### 1. Jira Tickets Found
        Found **{len(tickets)}** tickets.
        
        ### 2. Impact Analysis
        Analyzed **{len(impacts)}** items.
        
        ### 3. GitHub Actions
        {chr(10).join([f"- {issue}" for issue in issues])}
        """
        
        yield gr.update(value=output_md, visible=True)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        yield gr.update(value=f"Error: {e}\n\nTraceback:\n{traceback.format_exc()}", visible=True)

with gr.Blocks(title="Autonomous Change Management") as demo:
    gr.Markdown(
        """
        # 🤖 Autonomous Change Management Assistant
        ### Powered by Google ADK & Gemini
        """
    )
    
    with gr.Row():
        start_btn = gr.Button("Start Analysis", variant="primary", scale=1)
    
    output_display = gr.Markdown("Ready to start...", visible=True)
    
    start_btn.click(run_analysis, [], [output_display])

if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft())
