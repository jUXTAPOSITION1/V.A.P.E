import os
from dotenv import load_dotenv
from groq import Groq
from .wallet import AgentWallet
from .acp import ACPProtocol

load_dotenv()

class VAPE:
    def __init__(self):
        self.wallet = AgentWallet("VAPE")
        self.acp = ACPProtocol("VAPE")
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.system_prompt = open("agents/vape_system.md", "r").read()

    def think(self, query):
        """Real LLM reasoning with Groq"""
        response = self.client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.7,
            max_tokens=2048
        )
        return response.choices[0].message.content

    def run_investigation(self, target):
        """Real workflow example"""
        self.acp.request_service("on_chain_forensics", {"target": target})
        result = self.think(f"Investigate {target} on Base/Virtuals. Use real tools.")
        print(f"[VAPE] Investigation result:\n{result}")
        return result

if __name__ == "__main__":
    vape = VAPE()
    vape.run_investigation("0x... suspicious contract")
