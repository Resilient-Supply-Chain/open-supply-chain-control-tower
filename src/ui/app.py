from __future__ import annotations

import json
from pathlib import Path
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

    def respond(message, history, selected_model):
        reply = generate_reply(
            project_root=project_root,
            user_message=message,
            model_override=selected_model or None,
        )
        # If an email was sent, trigger a formal browser notification
        if "✅" in reply:
            gr.Info("COMMUNICATION PROTOCOL: Resilience Alert Broadcasted to Stakeholders")
            
        history = history + [{"role": "user", "content": message}, {"role": "assistant", "content": reply}]
        return "", history, get_alerts()

    with gr.Blocks(title="AI Control Tower", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🏛️ AI Control Tower: Supply-Chain Resilience")
        
        with gr.Tabs():
            # TAB 1: OPERATOR CONSOLE
            with gr.TabItem("📡 Analyst Console"):
                chatbot = gr.Chatbot(height=500)
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
