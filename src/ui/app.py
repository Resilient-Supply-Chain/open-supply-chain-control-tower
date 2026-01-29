from __future__ import annotations

from pathlib import Path
import time

import gradio as gr

from src.agents.chatbot import generate_reply, list_local_models
from src.tools.demo_runner import run_demo_presentation


def launch_app(*, agent_graph) -> None:
    project_root = Path(__file__).resolve().parents[2]

    def respond(
        message: str,
        history: list[dict[str, str]],
        selected_model: str,
        show_debug: bool,
        mode_state: str,
    ):
        demo_trigger = mode_state == "demo" and "demo" in message.lower()
        history = history + [{"role": "user", "content": message}]

        if demo_trigger:
            steps = [
                "⏳ Step 1/4: Locating provider data...",
                "⏳ Step 2/4: Converting data into UI-ready JSON...",
                "⏳ Step 3/4: Sending data to the UI layer...",
                "⏳ Step 4/4: Preparing dashboard link...",
            ]
            for step in steps:
                history = history + [{"role": "assistant", "content": step}]
                yield "", history
                time.sleep(1)
                history.pop()

            demo_result = run_demo_presentation(project_root=project_root)
            reply = (
                f"{demo_result.get('message')}\n"
                f"Open the demo: {demo_result.get('demo_url')}"
            )
            content = f"[Mode: demo] {reply}"
            history = history + [{"role": "assistant", "content": content}]
            yield "", history
            return

        reply, intent, thoughts = generate_reply(
            project_root=project_root,
            user_message=message,
            agent_graph=agent_graph,
            model_override=selected_model or None,
            mode_override=mode_state,
        )
        status = f"[Mode: {mode_state}] "
        content = status + reply
        if show_debug:
            debug_block = "\n\n---\nDebug Info:\n"
            debug_block += f"- intent: {intent}\n"
            if thoughts:
                debug_block += "- thought_history:\n" + "\n".join(
                    [f"  - {t}" for t in thoughts[-5:]]
                )
            content = content + debug_block
        history = history + [
            {"role": "assistant", "content": content},
        ]
        yield "", history

    css = """
    body, .gradio-container {
      font-family: 'Inter', 'SF Pro Rounded', 'Segoe UI', sans-serif;
    }
    #chat-shell {
      width: 100%;
    }
    #chat-card {
      width: 100%;
      border-radius: 18px;
      padding: 18px 22px;
    }
    #chat-row {
      align-items: flex-start;
    }
    #message-row {
      margin-top: 10px;
    }
    #message-row .gr-textbox {
      border-radius: 999px;
    }
    #control-row {
      align-items: center;
    }
    #control-row .gr-dropdown {
      max-width: 360px;
    }
    #mode-buttons {
      display: flex;
      gap: 8px;
      justify-content: flex-end;
      flex: 0 0 20%;
      max-width: 20%;
    }
    #mode-buttons .gr-button {
      border-radius: 10px;
      min-width: 0;
      padding: 6px 10px;
      font-size: 12px;
    }
    """
    with gr.Blocks(title="AI Control Tower Chatbot", css=css) as demo:
        gr.Markdown("# AI Control Tower Chatbot (Local LLM)")
        models = list_local_models()
        status_text = (
            "✅ Ollama detected. Select a model below."
            if models
            else "⚠ Ollama not found or no models installed. "
            "Install Ollama and run `ollama pull <model>`."
        )
        gr.Markdown(f"Status: {status_text}")
        mode_state = gr.State("react")
        with gr.Row(elem_id="chat-shell"):
            with gr.Column(elem_id="chat-card"):
                with gr.Row(elem_id="control-row"):
                    with gr.Column(scale=8):
                        model_selector = gr.Dropdown(
                            choices=models,
                            value=models[0] if models else None,
                            label="Local Model",
                        )
                    with gr.Column(scale=2, elem_id="mode-buttons"):
                        demo_mode = gr.Button("Demo", variant="secondary")
                        react_mode = gr.Button("ReAct", variant="primary")
                        clear = gr.Button("Clear")

                show_debug = gr.Checkbox(label="Show Debug Info", value=False)

                with gr.Row(elem_id="chat-row"):
                    chatbot = gr.Chatbot(height=480, value=[])

                with gr.Row(elem_id="message-row"):
                    msg = gr.Textbox(
                        label="Message",
                        placeholder="Ask a question...",
                        container=False,
                    )

        msg.submit(
            respond,
            [msg, chatbot, model_selector, show_debug, mode_state],
            [msg, chatbot],
        )

        def _set_demo_mode():
            return (
                "demo",
                [],
                gr.update(variant="primary"),
                gr.update(variant="secondary"),
            )

        def _set_react_mode():
            return (
                "react",
                [],
                gr.update(variant="secondary"),
                gr.update(variant="primary"),
            )

        demo_mode.click(
            _set_demo_mode,
            None,
            [mode_state, chatbot, demo_mode, react_mode],
            queue=False,
        )
        react_mode.click(
            _set_react_mode,
            None,
            [mode_state, chatbot, demo_mode, react_mode],
            queue=False,
        )
        clear.click(lambda: [], None, chatbot, queue=False)

    demo.launch()


__all__ = ["launch_app"]

