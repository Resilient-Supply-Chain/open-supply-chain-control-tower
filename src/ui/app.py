from __future__ import annotations

import json
from pathlib import Path
import random
import time
import re
import gradio as gr

from src.agents.chatbot import generate_reply, list_local_models

ALERT_LOG = Path("data/output/alerts.json")

def get_alerts():
    if not ALERT_LOG.exists():
        return []
    try:
        with open(ALERT_LOG, "r") as f:
            data = json.load(f)
            # Convert list of dicts to list of lists to match headers
            # Headers: Timestamp, Target Region, Risk Coefficient, Designated Stakeholder, Operational Status
            return [
                [
                    item.get("timestamp"),
                    item.get("location"),
                    item.get("score"),
                    item.get("recipient"),
                    item.get("status")
                ]
                for item in data
            ]
    except:
        return []

def launch_app() -> None:
    project_root = Path(__file__).resolve().parents[2]
    persona_intro = (
        "Hello. I am an AI Control Tower agent aligned with the S.257 proposal to "
        "strengthen U.S. supply-chain resilience.\n\n"
        "Current capabilities:\n"
        "1) Secure, confidence-focused dialogue.\n"
        "2) Power outage risk prediction and dashboard summaries.\n"
        "3) Resilience alert reporting via email broadcasts.\n"
        "4) High-confidence answers grounded in local sensitive datasets (RAG)."
    )

    def _workflow_steps(message: str) -> list[str]:
        lower_message = message.lower()
        if re.search(r"today is (\d{4}-\d{2}-\d{2})", lower_message):
            return [
                "[] Validating date and recipient metadata.",
                "[] Loading risk data for the target date.",
                "[] Filtering for high-risk events.",
                "[] Dispatching resilience alert via SES.",
                "[] Logging alert status to the dashboard.",
            ]
        if "demo" in lower_message:
            return [
                "[] Validating demo workflow request.",
                "[] Locating registered provider datasets.",
                "[] Converting provider data to UI-ready JSON.",
                "[] Preparing dashboard output artifacts.",
            ]
        company_match = re.search(
            r"(?:for the company|company)\s+([a-z0-9\s\-]+?)(?:,|\?|$)",
            lower_message,
        )
        company_name = company_match.group(1).strip() if company_match else ""
        if "asteria circuits" in lower_message or company_name == "asteria circuits":
            return [
                "[] Identifying target entity in local records.",
                "[] Loading the pseudo company knowledge index.",
                "[] Retrieving relevant supply-chain snippets.",
                "[] Assembling a grounded response.",
            ]
        return []

    def respond(message, history, selected_model):
        history = history + [{"role": "user", "content": message}]
        yield "", history, get_alerts()

        for step in _workflow_steps(message):
            history = history + [{"role": "assistant", "content": step}]
            yield "", history, get_alerts()
            time.sleep(random.uniform(3, 5))

        reply = generate_reply(
            project_root=project_root,
            user_message=message,
            model_override=selected_model or None,
        )
        # If an email was sent, trigger a formal browser notification
        if "✅" in reply:
            gr.Info("COMMUNICATION PROTOCOL: Resilience Alert Broadcasted to Stakeholders")

        history = history + [{"role": "assistant", "content": reply}]
        yield "", history, get_alerts()

    with gr.Blocks(title="AI Control Tower", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🏛️ AI Control Tower: Supply-Chain Resilience")
        
        with gr.Tabs():
            # TAB 1: OPERATOR CONSOLE
            with gr.TabItem("📡 Analyst Console"):
                chatbot = gr.Chatbot(
                    height=500,
                    value=[{"role": "assistant", "content": persona_intro}],
                )
                msg = gr.Textbox(label="Decision Support Query", placeholder="Enter query or use broadcast action below...")
                with gr.Row():
                    models = list_local_models()
                    model_selector = gr.Dropdown(choices=models, value=models[0] if models else None, label="Active Intelligence Model")

            # TAB 2: AGENCY DASHBOARD
            with gr.TabItem("📊 Agency Oversight Dashboard"):
                gr.Markdown("## 📋 Automated Notification Log")
                alert_table = gr.Dataframe(
                    headers=["Timestamp", "Target Region", "Risk Coefficient", "Designated Stakeholder", "Operational Status"],
                    value=get_alerts(),
                    interactive=False
                )
                refresh_btn = gr.Button("Sync Dashboard Data")

        # Logic
        msg.submit(respond, [msg, chatbot, model_selector], [msg, chatbot, alert_table])
        refresh_btn.click(get_alerts, None, alert_table)

    demo.launch()
