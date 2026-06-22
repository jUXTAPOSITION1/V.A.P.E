from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv
import os

load_dotenv()

class AgentWallet:
    def __init__(self, agent_name="VAPE"):
        self.agent_name = agent_name
        self.w3_base = Web3(Web3.HTTPProvider("https://mainnet.base.org"))
        
        # Load private key from .env (NEVER commit this)
        private_key = os.getenv(f"{agent_name}_PRIVATE_KEY")
        if private_key:
            self.account = Account.from_key(private_key)
            self.address = self.account.address
            print(f"[{agent_name}] Wallet loaded: {self.address}")
        else:
            print(f"[{agent_name}] Warning: No private key in .env - using read-only mode")
            self.address = None

    def get_balance(self):
        if not self.address:
            return 0
        return self.w3_base.eth.get_balance(self.address) / 10**18

# Create .env file in root with:
# VAPE_PRIVATE_KEY=0x...
# HACK_PRIVATE_KEY=0x...
