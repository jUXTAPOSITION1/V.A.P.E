import gradio as gr
from datetime import datetime
import sqlite3

conn = sqlite3.connect("vape_memory.db")
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS memory (timestamp TEXT, content TEXT)")

def save_memory(content):
    c.execute("INSERT INTO memory VALUES (?, ?)", (datetime.now().isoformat(), content))
    conn.commit()

def ask_vape(query):
    result = f"VAPE: I received your message: {query[:200]}... (Local mode)"
    save_memory(f"User: {query}\nVAPE: {result}")
    return result

def git_sync():
    return "GitHub sync ready (add token later)"

with gr.Blocks(title="VAPE - Private Agent") as demo:
    gr.Markdown("# VAPE • Private Mobile Agent")
    gr.Markdown("Full control • Local • Growing")

    with gr.Tab("Chat"):
        query = gr.Textbox(label="Talk to VAPE or give command")
        output = gr.Textbox(label="VAPE Response")
        gr.Button("Send").click(ask_vape, inputs=query, outputs=output)

    with gr.Tab("GitHub"):
        gr.Button("Sync to GitHub").click(git_sync)

    with gr.Tab("Memory"):
        gr.Button("Show Recent Memory").click(lambda: "Memory from DB loaded")

demo.launch()
