import os
from dotenv import load_dotenv
from datetime import datetime
import sys
import time
import requests

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def ask_llm(system, query):
    for attempt in range(3):
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
            data = {"contents": [{"parts": [{"text": f"{system}\n\n{query}"}]}]}
            response = requests.post(url, json=data)
            return response.json()["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            print(f"Error: {str(e)}. Waiting 30s... (attempt {attempt+1}/3)")
            time.sleep(30)
    return "Rate limit persistent. Try later."

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

if __name__ == "__main__":
    review = "--review-repo" in sys.argv
    main(review)
