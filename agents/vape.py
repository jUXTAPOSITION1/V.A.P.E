import os
from dotenv import load_dotenv
from .wallet import AgentWallet
from .acp import ACPProtocol

load_dotenv()

class VAPE:
    def __init__(self):
        self.wallet = AgentWallet("VAPE")
        self.acp = ACPProtocol("VAPE")
        self.system_prompt = open("agents/vape_system.md", "r", encoding="utf-8").read()

    def think(self, query):
        """Simple placeholder for LLM"""
        return f"[VAPE Thinking]\nQuery: {query[:500]}\n\nAnalysis complete. Ready for action."

    def run_investigation(self, target):
        self.acp.request_service("on_chain_forensics", {"target": target})
        result = self.think(f"Investigate {target} on Base and Virtuals.")
        print(f"[VAPE] Result:\n{result}")
        return result

if __name__ == "__main__":
    vape = VAPE()
    vape.run_investigation("example contract")
