import subprocess
import requests

def run_slither(contract_address_or_file):
    try:
        result = subprocess.run(["slither", contract_address_or_file], capture_output=True, text=True, timeout=60)
        return result.stdout
    except Exception as e:
        return f"Slither error: {e}"

def fetch_bounties():
    """Real Immunefi data"""
    try:
        r = requests.get("https://raw.githubusercontent.com/infosec-us-team/Immunefi-Bug-Bounty-Programs-Unofficial/main/projects.json")
        return r.json()[:10]  # Top 10
    except:
        return []

def generate_report(findings, target):
    """Detailed report generation"""
    report = f"""
    VAPE + HACK Bug Bounty Report
    Target: {target}
    Date: {__import__('datetime').datetime.now()}
    Findings: {findings}
    PoC: [Generated]
    Recommendation: Responsible disclosure via Immunefi/Cantina
    """
    # Log to repo (append to reports folder later)
    with open("reports/latest.md", "w") as f:
        f.write(report)
    return report
