from __future__ import annotations

from pathlib import Path

import gradio as gr

from src.agents.chatbot import generate_reply, list_local_models


def launch_app(*, agent_graph) -> None:
    project_root = Path(__file__).resolve().parents[2]

    def respond(
        message: str,
        history: list[dict[str, str]],
        selected_model: str,
    ) -> tuple[str, list[dict[str, str]]]:
        reply = generate_reply(
            project_root=project_root,
            user_message=message,
            agent_graph=agent_graph,
            model_override=selected_model or None,
        )
        history = history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": reply},
        ]
        return "", history

    with gr.Blocks(title="AI Control Tower Chatbot") as demo:
        gr.Markdown("# AI Control Tower Chatbot (Local LLM)")
        models = list_local_models()
        status_text = (
            "✅ Ollama detected. Select a model below."
            if models
            else "⚠ Ollama not found or no models installed. "
            "Install Ollama and run `ollama pull <model>`."
        )
        gr.Markdown(f"Status: {status_text}")
        model_selector = gr.Dropdown(
            choices=models,
            value=models[0] if models else None,
            label="Local Model",
        )
        chatbot = gr.Chatbot(height=420, value=[])
        msg = gr.Textbox(label="Message", placeholder="Ask a question...")
        clear = gr.Button("Clear")

        msg.submit(respond, [msg, chatbot, model_selector], [msg, chatbot])
        clear.click(lambda: [], None, chatbot, queue=False)

    demo.launch()


__all__ = ["launch_app"]

