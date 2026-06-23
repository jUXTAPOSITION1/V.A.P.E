from agents.vape import VAPE
from agents.hack import HACK
from agents.tools import fetch_bounties, log_report

def main():
    print("VAPE + HACK Autonomous Bug Bounty Cycle Started")
    vape = VAPE()
    hack = HACK()
    
    bounties = fetch_bounties()
    print(f"Found {len(bounties)} bounties")
    
    for bounty in bounties[:3]:
        target = bounty.get("name", "unknown")
        print(f"Processing {target}")
        
        intel = vape.run_investigation(target)
        audit = hack.audit_contract(target)
        report = log_report(target, audit)
        print(report)
    
    print("Cycle complete. Reports logged.")

if __name__ == "__main__":
    main()
