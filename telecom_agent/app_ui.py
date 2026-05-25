"""
Telecom Incident Analyzer - Gradio UI
A minimal, decorated interface for the multi-agent telecom incident resolution system.
Accepts ticket inputs and outputs actionable resolution steps.
"""

import os
import sys
import csv
import io
import warnings
from datetime import datetime

# Suppress dependency deprecation warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message="Core Pydantic V1 functionality")
warnings.filterwarnings("ignore", message="allowed_objects")

# Resolve SSL and path conflicts
import ssl
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
os.environ["PYTHONHTTPSVERIFY"] = "0"
os.environ["REQUESTS_CABUNDLE"] = ""
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gradio as gr
from workflow import build_workflow
from langgraph.checkpoint.memory import MemorySaver


def process_incident_ticket(created_at, subject, description, region, affected_service):
    """
    Processes a telecom incident ticket through the multi-agent workflow.
    Returns a formatted string of actionable steps and ticket details.
    """
    try:
        # Construct a CSV row from inputs
        csv_row = f"TKT-AUTO,{created_at},CUST-AUTO,{region},{subject},{description},{affected_service},Web,Open"

        # Parse CSV
        f = io.StringIO(csv_row.strip())
        reader = csv.reader(f)
        row = next(reader)
        headers = ["ticket_id", "created_at", "customer_id", "region", "subject", "description", "affected_service", "channel", "status"]
        ticket_row = dict(zip(headers, row))

        # Build initial state
        initial_state = {
            "ticket_id": ticket_row.get("ticket_id", "TKT-UNKNOWN"),
            "ticket_created_at": ticket_row.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            "ticket_customer_id": ticket_row.get("customer_id", "CUST-UNKNOWN"),
            "ticket_region": ticket_row.get("region", "Central"),
            "ticket_subject": ticket_row.get("subject", "No Subject"),
            "ticket_description": ticket_row.get("description", ""),
            "ticket_affected_service": ticket_row.get("affected_service", "General"),
            "ticket_channel": ticket_row.get("channel", "Web"),
            "ticket_status": ticket_row.get("status", "Open"),

            "ticket_category": None,
            "outage_data": None,
            "priority": None,
            "impact_score": None,
            "severity_reasoning": None,

            "resolution_summary": None,
            "resolution_root_cause": None,
            "resolution_steps": None,
            "confidence_score": 0.0,

            "tavily_query": None,
            "tavily_results": None,

            "approved": None,
            "approval_risk": None,
            "approval_concerns": None,
            "approval_modifications": None,
            "approval_notes": None,

            "final_resolution": None,

            "loop_count": 0,
            "processing_log": []
        }

        # Run workflow
        checkpointer = MemorySaver()
        workflow_graph = build_workflow().compile(checkpointer=checkpointer)

        thread_id = f"ui-{datetime.now().timestamp()}"
        config = {"configurable": {"thread_id": thread_id}}

        final_state = workflow_graph.invoke(initial_state, config=config)

        # Format output
        output = ""
        output += f"📋 **TICKET ANALYSIS RESULT**\n\n"
        output += f"**Category:** {final_state.get('ticket_category', 'N/A')}\n"
        output += f"**Priority:** {final_state.get('priority', 'N/A')} (Impact: {final_state.get('impact_score', 0):.2f})\n"
        output += f"**Issue Summary:** {final_state.get('resolution_summary', 'N/A')}\n"
        output += f"**Root Cause:** {final_state.get('resolution_root_cause', 'N/A')}\n"
        output += f"**Confidence Score:** {final_state.get('confidence_score', 0):.2f}\n"
        output += f"**Status:** {'✅ APPROVED' if final_state.get('approved') else '🔍 PENDING'}\n\n"

        output += f"🔧 **ACTIONABLE STEPS**\n\n"
        steps = final_state.get("final_resolution", [])
        if steps:
            for i, step in enumerate(steps, 1):
                output += f"{i}. {step}\n"
        else:
            output += "No steps found. Please check the ticket details.\n"

        return output

    except Exception as e:
        return f"❌ Error processing ticket: {str(e)}\n\nPlease ensure all fields are filled correctly and try again."


def create_ui():
    """
    Creates a professional and light-colored Gradio interface for the telecom incident analyzer.
    """
    # Professional light theme CSS
    custom_css = """
    body {
        background: linear-gradient(135deg, #f8fafc 0%, #f0f4f8 100%);
    }
    .gradio-container {
        background: #ffffff;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    }
    .header-section {
        background: linear-gradient(135deg, #e8f1f8 0%, #f0f5f9 100%);
        padding: 30px;
        border-radius: 8px;
        border-left: 5px solid #0066cc;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0, 102, 204, 0.08);
    }
    .header-section h1 {
        color: #1a3a52;
        font-weight: 600;
    }
    .header-section p {
        color: #4a5f7f;
    }
    .input-section {
        background: linear-gradient(135deg, #f5f9fc 0%, #f1f6fa 100%);
        padding: 20px;
        border-radius: 8px;
        border-left: 4px solid #0066cc;
        box-shadow: 0 2px 6px rgba(0, 102, 204, 0.06);
    }
    .input-section h2 {
        color: #1a3a52;
        font-weight: 600;
        margin-top: 0;
    }
    .input-section p {
        color: #6b7c8f;
    }
    .output-section {
        background: linear-gradient(135deg, #f0f7ff 0%, #f2f8fc 100%);
        padding: 20px;
        border-radius: 8px;
        border-left: 4px solid #0066cc;
        box-shadow: 0 2px 6px rgba(0, 102, 204, 0.06);
    }
    .output-section h2 {
        color: #1a3a52;
        font-weight: 600;
        margin-top: 0;
    }
    .output-section p {
        color: #6b7c8f;
    }
    .examples-section {
        background: linear-gradient(135deg, #f5fdf9 0%, #f1faf7 100%);
        padding: 20px;
        border-radius: 8px;
        border-left: 4px solid #00a884;
        box-shadow: 0 2px 6px rgba(0, 168, 132, 0.06);
    }
    .examples-section h2 {
        color: #1a3a52;
        font-weight: 600;
        margin: 0 0 10px 0;
    }
    .examples-section p {
        color: #6b7c8f;
        margin: 0;
    }
    .about-section {
        background: linear-gradient(135deg, #fefdf8 0%, #faf8f3 100%);
        padding: 20px;
        border-radius: 8px;
        border-left: 4px solid #e8a400;
        box-shadow: 0 2px 6px rgba(232, 164, 0, 0.06);
    }
    .about-section h2 {
        color: #1a3a52;
        font-weight: 600;
        margin: 0 0 15px 0;
    }
    """

    with gr.Blocks(
        title="Telecom Incident Resolution Agent",
        css=custom_css
    ) as demo:

        # Header Section
        gr.HTML("""
        <div class="header-section">
            <h1 style="margin: 0; font-size: 2.5em; color: #0066cc;">
                Telecom Incident Resolution Agent
            </h1>
            <p style="font-size: 1.2em; margin: 10px 0; color: #4a5f7f; font-weight: 500;">
                AI-Powered Ticket Analysis & Resolution Planning
            </p>
            <p style="font-size: 1em; margin: 0; color: #6b7c8f;">
                Multi-Agent System for Intelligent Incident Management
            </p>
        </div>
        """)

        gr.HTML("<br>")

        with gr.Row():
            with gr.Column(scale=1):
                gr.HTML("""
                <div class="input-section">
                    <h2 style="color: #0066cc; margin-top: 0;">
                        Incident Details
                    </h2>
                    <p style="color: #6b7c8f;">Fill in the ticket information below</p>
                </div>
                """)

                # Input fields
                created_at_input = gr.Textbox(
                    label="Created At",
                    placeholder="YYYY-MM-DD HH:MM:SS",
                    value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    info="Ticket creation timestamp"
                )

                subject_input = gr.Textbox(
                    label="Subject",
                    placeholder="Brief title of the incident",
                    info="Short summary of the issue"
                )

                description_input = gr.Textbox(
                    label="Description",
                    placeholder="Detailed description of the incident",
                    lines=4,
                    info="Full technical details of the problem"
                )

                region_input = gr.Textbox(
                    label="Region",
                    placeholder="e.g., Mumbai, Delhi, Bangalore",
                    info="Geographic region affected"
                )

                affected_service_input = gr.Textbox(
                    label="Affected Service",
                    placeholder="e.g., Mobile Data, Voice, VoLTE",
                    info="Service impacted by the incident"
                )

                gr.HTML("<br>")

                submit_btn = gr.Button(
                    "Analyze Ticket",
                    variant="primary",
                    size="lg",
                    scale=1
                )

            with gr.Column(scale=1):
                gr.HTML("""
                <div class="output-section">
                    <h2 style="color: #0066cc; margin-top: 0;">
                        Analysis Output
                    </h2>
                    <p style="color: #6b7c8f;">Real-time AI-powered resolution steps</p>
                </div>
                """)

                # Output field
                output_display = gr.Markdown(
                    value="""
                    <div style="background: #f5f9fc; padding: 20px; border-radius: 8px; border-left: 4px solid #0066cc; color: #4a5f7f;">
                        <h3 style="color: #0066cc; margin-top: 0;">Waiting for analysis...</h3>
                        <p>Fill in the incident details and click "Analyze Ticket" to see results here.</p>
                    </div>
                    """,
                    label="Resolution Steps"
                )

        gr.HTML("<br>")

        # Examples section
        gr.HTML("""
        <div class="examples-section">
            <h2 style="color: #00a884; margin: 0 0 10px 0;">
                Example Tickets - Quick Start
            </h2>
            <p style="color: #6b7c8f; margin: 0;">
                Click on any example below to see how the system works in action!
            </p>
        </div>
        """)

        example_tickets = [
            [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "No signal in south region",
                "Customer is getting no signal since 7 AM. Phone shows 'No Service'. Restarting phone did not help. Neighbours also facing the same issue.",
                "Mumbai",
                "Mobile Data"
            ],
            [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Voice service degradation",
                "Voice calls are experiencing high latency and occasional drops. Customer reports call quality issues on all outbound calls. Problem started 2 hours ago.",
                "Delhi",
                "Voice"
            ],
            [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Modem not connecting",
                "Customer's home broadband modem is not connecting to the network. LED indicators show red. Device restart did not resolve the issue.",
                "Bangalore",
                "Broadband"
            ]
        ]

        gr.Examples(
            examples=example_tickets,
            inputs=[created_at_input, subject_input, description_input, region_input, affected_service_input],
            outputs=output_display,
            fn=process_incident_ticket,
            cache_examples=False,
            label="Sample Tickets"
        )

        gr.HTML("<br>")

        gr.HTML("""
        <div class="about-section">
            <h2 style="color: #e8a400; margin: 0 0 15px 0;">
                About This System
            </h2>
        </div>
        """)

        gr.Markdown("""
        ### Multi-Agent Workflow Architecture

        | Agent | Purpose | Function |
        |:---|:---|:---|
        | **Classification Agent** | Categorizes incidents | Network, Service, Hardware, Customer Experience |
        | **Severity Agent** | Assigns priority & risk | P1-P4 levels + Impact scores |
        | **Resolution Agent** | Generates fix plans | RAG-enhanced troubleshooting |
        | **Search Agent** | Web search fallback | For low-confidence cases |
        | **Approval Agent** | Human review gating | Safety & validation |

        ### Technology Stack

        - **LangGraph** - Workflow orchestration
        - **Gemini 2.5 Flash** - AI reasoning engine
        - **ChromaDB** - Vector database for RAG
        - **SentenceTransformer** - Embedding model
        - **Tavily API** - Web search integration
        """)

        gr.HTML("<br>")

        # Connect submit button
        submit_btn.click(
            fn=process_incident_ticket,
            inputs=[created_at_input, subject_input, description_input, region_input, affected_service_input],
            outputs=output_display
        )

    return demo


if __name__ == "__main__":
    demo = create_ui()
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        show_error=True,
        theme=gr.themes.Soft(
            primary_hue="blue",
            secondary_hue="slate"
        )
    )
 