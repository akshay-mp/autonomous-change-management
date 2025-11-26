import gradio as gr
import os
import asyncio
from orchestrator import ChangeManagementOrchestrator

JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_BASE_URL = os.getenv("JIRA_BASE_URL")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GITHUB_PERSONAL_ACCESS_TOKEN = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")

async def run_analysis():
    orchestrator = ChangeManagementOrchestrator()
    
    # We can yield progress updates here if we modify the orchestrator to yield
    # For now, we'll just run it and return the final result
    
    results = []
    log_content = ""
    yield gr.update(value="Starting Analysis...", visible=True), gr.update(value="Starting...", visible=True)
    
    try:
        # Run the orchestrator
        final_context = {}
        async for update in orchestrator.run_with_progress():
            if isinstance(update, str):
                log_content += update + "\n"
                yield gr.update(value=log_content), gr.update()
            else:
                final_context = update
        
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
        
        yield gr.update(value=log_content), gr.update(value=output_md, visible=True)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        error_msg = f"Error: {e}\n\nTraceback:\n{traceback.format_exc()}"
        yield gr.update(value=log_content + "\n" + error_msg), gr.update(value="Analysis Failed", visible=True)

with gr.Blocks(title="Autonomous Change Management") as demo:
    gr.Markdown(
        """
        # 🤖 Autonomous Change Management Assistant
        ### Powered by Google ADK & Gemini
        """
    )
    
    with gr.Row():
        start_btn = gr.Button("Start Analysis", variant="primary", scale=1)
    
    log_output = gr.Textbox(label="Workflow Log", lines=10, interactive=False)
    output_display = gr.Markdown("Ready to start...", visible=True)
    
    start_btn.click(run_analysis, [], [log_output, output_display])

if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft())