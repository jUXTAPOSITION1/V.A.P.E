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

def self_review_and_improve():
    """VAPE reviews its own code and outputs actionable diffs"""
    code_context = "Review the agents folder and output concrete code diffs or new functions that can be directly applied."
    improvement_plan = ask_llm(
        "You are VAPE. When suggesting improvements, always output concrete code diffs in patch format that can be applied.",
        code_context
    )
    report = f"# Self-Improvement Report - {datetime.now()}\n\n{improvement_plan}"
    with open(f"reports/self_improve_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md", "w") as f:
        f.write(report)
    print("Self-improvement with code diffs generated.")
    return improvement_plan

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
    
    # Self-improvement with code diffs
    self_review_and_improve()

if __name__ == "__main__":
    review = "--review-repo" in sys.argv
    main(review)
