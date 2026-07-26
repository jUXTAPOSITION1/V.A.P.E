"""One-off script: mint VAPE's own ERC-8004 agent identity on Base mainnet,
decoupling VAPE's on-chain identity from Virtuals Protocol's ACP agent
registry (previously agent #54988, https://app.virtuals.io/acp/agent/...).

Calls register(agentURI) directly on the canonical ERC-8004 IdentityRegistry
contract (same address across every chain it's deployed to -- confirmed
against erc-8004/erc-8004-contracts) rather than driving Chitin's web UI:
Chitin's dApp is itself just a UI wrapper over this exact contract, and
automating a live wallet-connect flow with a real signing key is both
fragile and worse security hygiene than a reviewable, scripted transaction.

agentURI points at docs/agent-metadata.json served from VAPE's own GitHub
Pages site rather than Arweave -- no funded Arweave/Irys account exists to
pay for that upload, the on-chain agentId itself is what actually matters
for identity, and the metadata can be re-pointed later via setAgentURI() if
it ever needs to move.

Usage: DATA_AGENT_PRIVATE_KEY=... python3 scripts/register_erc8004_identity.py
"""
import json
import os
import sys
import time

from eth_account import Account
from web3 import Web3

BASE_RPC = os.getenv("BASE_RPC_URL", "https://mainnet.base.org")
IDENTITY_REGISTRY = Web3.to_checksum_address("0x8004A169FB4a3325136EB29fA0ceB6D2e539a432")
AGENT_URI = "https://juxtaposition1.github.io/V.A.P.E/agent-metadata.json"
# Must match the wallet address the user gave for this registration -- the
# same safety check agents/data_agent.py already applies to this exact key
# (EXPECTED_WALLET) before it's trusted to act.
EXPECTED_WALLET = "0x8aAB9a6d28e9AbA2a15a613C90F24f352f0Cce15"

ABI = [
    {
        "inputs": [{"internalType": "string", "name": "agentURI", "type": "string"}],
        "name": "register",
        "outputs": [{"internalType": "uint256", "name": "agentId", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "uint256", "name": "agentId", "type": "uint256"},
            {"indexed": False, "internalType": "string", "name": "agentURI", "type": "string"},
            {"indexed": True, "internalType": "address", "name": "owner", "type": "address"},
        ],
        "name": "Registered",
        "type": "event",
    },
]


def main():
    key = os.getenv("DATA_AGENT_PRIVATE_KEY")
    if not key:
        print("::error::DATA_AGENT_PRIVATE_KEY not set", file=sys.stderr)
        sys.exit(1)

    account = Account.from_key(key)
    if account.address.lower() != EXPECTED_WALLET.lower():
        print(f"::error::DATA_AGENT_PRIVATE_KEY derives {account.address}, "
              f"expected {EXPECTED_WALLET} -- refusing to register under the wrong wallet.",
              file=sys.stderr)
        sys.exit(1)

    w3 = Web3(Web3.HTTPProvider(BASE_RPC))
    if not w3.is_connected():
        print(f"::error::Could not connect to Base RPC at {BASE_RPC}", file=sys.stderr)
        sys.exit(1)

    registry = w3.eth.contract(address=IDENTITY_REGISTRY, abi=ABI)

    # Simulate first (eth_call, no state change) so a revert (wrong network,
    # contract paused, etc.) is caught before any real gas is spent.
    try:
        simulated_id = registry.functions.register(AGENT_URI).call({"from": account.address})
        print(f"Simulated call OK -- would-be agentId: {simulated_id}")
    except Exception as e:
        print(f"::error::Simulation reverted, refusing to send a real transaction: {e}", file=sys.stderr)
        sys.exit(1)

    nonce = w3.eth.get_transaction_count(account.address)
    tx = registry.functions.register(AGENT_URI).build_transaction({
        "from": account.address,
        "nonce": nonce,
        "chainId": 8453,
        "gasPrice": w3.eth.gas_price,
    })
    tx["gas"] = int(w3.eth.estimate_gas(tx) * 1.2)

    signed = account.sign_transaction(tx)
    raw = getattr(signed, "raw_transaction", None) or signed.rawTransaction
    tx_hash = w3.eth.send_raw_transaction(raw)
    print(f"Sent tx: {tx_hash.hex()}")
    print(f"Basescan: https://basescan.org/tx/{tx_hash.hex()}")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    if receipt.status != 1:
        print(f"::error::Transaction reverted. Receipt: {dict(receipt)}", file=sys.stderr)
        sys.exit(1)

    agent_id = None
    for log in receipt.logs:
        try:
            event = registry.events.Registered().process_log(log)
            agent_id = event["args"]["agentId"]
            break
        except Exception:
            continue

    result = {
        "agent_id": agent_id,
        "wallet": account.address,
        "tx_hash": tx_hash.hex(),
        "contract": IDENTITY_REGISTRY,
        "agent_uri": AGENT_URI,
        "basescan_tx": f"https://basescan.org/tx/{tx_hash.hex()}",
        "basescan_token": (f"https://basescan.org/token/{IDENTITY_REGISTRY}?a={agent_id}"
                            if agent_id is not None else None),
        "registered_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    print(f"::notice::VAPE ERC-8004 agentId={agent_id} wallet={account.address} tx={tx_hash.hex()}")
    print(json.dumps(result, indent=2))

    out_path = os.getenv("GITHUB_OUTPUT")
    if out_path and agent_id is not None:
        with open(out_path, "a") as f:
            f.write(f"agent_id={agent_id}\n")
            f.write(f"tx_hash={tx_hash.hex()}\n")


if __name__ == "__main__":
    main()
