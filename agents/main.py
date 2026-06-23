import sys
sys.path.append('/home/runner/work/V.A.P.E/V.A.P.E')
from agents.vape import VAPE
from agents.hack import HACK
from agents.tools import fetch_bounties, generate_report

def main():
    print("Starting VAPE + HACK Autonomous Bug Bounty System")
    vape = VAPE()
    hack = HACK()
    bounties = fetch_bounties()
    print(f"Found {len(bounties)} potential bounties")
    for bounty in bounties[:3]:
        target = bounty.get("name", "unknown")
        print(f"\n--- Processing {target} ---")
        intel = vape.run_investigation(target)
        audit = hack.audit_contract("example")
        report = generate_report(audit, target)
        print(report)
    print("Cycle complete.")

if __name__ == "__main__":
    main()
