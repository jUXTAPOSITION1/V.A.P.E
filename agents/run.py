import os
from dotenv import load_dotenv
from groq import Groq
from datetime import datetime
import sys

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def ask_llm(system, query):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": query}
        ],
        temperature=0.7,
        max_tokens=4096
    )
    return response.choices[0].message.content

def red_team_test(target):
    """Red teaming module"""
    response = ask_llm(
        "You are a professional red teamer. Be technical and concrete.",
        f"Perform advanced red teaming on {target}. Include prompt injection, jailbreak, and agent workflow attacks."
    )
    return response

def propose_self_pr():
    """VAPE proposes a real PR for self-improvement"""
    response = ask_llm(
        "You are VAPE. Generate a full GitHub PR with title, description, and code diff for self-improvement.",
        "Analyze the agents folder and create a real PR proposal with code changes."
    )
    with open(f"reports/self_pr_proposal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md", "w") as f:
        f.write(f"# Self-PR Proposal - {datetime.now()}\n\n{response}")
    print("Self-PR proposal generated.")
    return response

def main(review_repo=False):
    print("VAPE + HACK Cycle Started")
    os.makedirs("reports", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if review_repo:
        report = ask_llm(
            "You are VAPE, a thorough repo reviewer. Provide concrete, actionable analysis without disclaimers.",
            "Review the entire repo structure, code, recent changes, and give detailed findings, bugs, and improvement suggestions."
        )
        report_path = f"reports/repo_review_{timestamp}.md"
    else:
        report = ask_llm(
            "You are VAPE + HACK, a real autonomous bug bounty agent. Provide concrete, actionable analysis without disclaimers or simulations.",
            "Run a full advanced bug bounty + red team cycle on Base and Virtuals. Include exploit simulation, jailbreak testing, smart contract analysis, and actionable recommendations."
        )
        report_path = f"reports/bounty_report_{timestamp}.md"
    
    with open(report_path, "w") as f:
        f.write(f"# VAPE Report - {timestamp}\n\n{report}")
    
    print(f"Report saved to: {report_path}")
    
    # Red teaming
    redteam_report = red_team_test("Base and Virtuals protocols")
    with open(f"reports/redteam_{timestamp}.md", "w") as f:
        f.write(f"# Red Team Report - {timestamp}\n\n{redteam_report}")
    
    print("Red team analysis complete.")
    
    # Self-PR proposal
    propose_self_pr()

if __name__ == "__main__":
    review = "--review-repo" in sys.argv
    main(review)
