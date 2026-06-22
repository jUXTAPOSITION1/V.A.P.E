
from vape import VAPE
from hack import HACK
from tools import fetch_bounties, generate_report

def main():
    print("Starting VAPE + HACK Autonomous Bug Bounty System")
    
    vape = VAPE()
    hack = HACK()
    
    bounties = fetch_bounties()
    print(f"Found {len(bounties)} potential bounties")
    
    for bounty in bounties[:3]:  # Top 3
        target = bounty.get("name", "unknown")
        print(f"\n--- Processing {target} ---")
        
        # VAPE investigates
        intel = vape.run_investigation(target)
        
        # HACK audits
        audit = hack.audit_contract("example_contract")  # Replace with real
        
        # Generate & log report
        report = generate_report(audit, target)
        print(report)
    
    print("Cycle complete. Reports logged to repo.")

if __name__ == "__main__":
    main()
