import gradio as gr

def ask_vape(query):
    return f"VAPE: I received your message: {query[:200]}... (Local mode)"

with gr.Blocks(title="VAPE - Private Agent") as demo:
    gr.Markdown("# VAPE • Private Mobile Agent")
    gr.Markdown("Full control • Local • Growing")

    query = gr.Textbox(label="Talk to VAPE or give command")
    output = gr.Textbox(label="VAPE Response")
    gr.Button("Send").click(ask_vape, inputs=query, outputs=output)

demo.launch()
