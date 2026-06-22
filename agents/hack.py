import os
from dotenv import load_dotenv
from groq import Groq
from .wallet import AgentWallet
from .acp import ACPProtocol
import subprocess

load_dotenv()

class HACK:
    def __init__(self):
        self.wallet = AgentWallet("HACK")
        self.acp = ACPProtocol("HACK")
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.system_prompt = open("agents/hack_system.md", "r").read()

    def think(self, query):
        response = self.client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.6,
            max_tokens=4096
        )
        return response.choices[0].message.content

    def audit_contract(self, contract_address):
        """Real tool execution example (Slither)"""
        self.acp.request_service("smart_contract_audit", {"contract": contract_address})
        
        try:
            # Real Slither execution (install Slither globally or via subprocess)
            result = subprocess.run(["slither", contract_address], capture_output=True, text=True, timeout=60)
            analysis = result.stdout
        except Exception as e:
            analysis = f"Tool error: {e}. Using LLM analysis."

        final_report = self.think(f"Audit {contract_address}. Raw data: {analysis[:2000]}")
        print(f"[HACK] Audit Report:\n{final_report}")
        return final_report

if __name__ == "__main__":
    hack = HACK()
    hack.audit_contract("0x...")  # Replace with real address
