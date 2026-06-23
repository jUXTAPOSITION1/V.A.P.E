import os
from dotenv import load_dotenv
from groq import Groq
from datetime import datetime
import sys

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def ask_llm(system, query):
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": query}
            ],
            temperature=0.7,
            max_tokens=2048
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

def main(review_repo=False):
    print("VAPE + HACK Cycle Started")
    os.makedirs("reports", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if review_repo:
        report = ask_llm(
            "You are VAPE, a thorough repo reviewer. Provide concrete, actionable analysis without disclaimers, simulations, or fictional examples. Use real data only. Always include concrete PoCs with code examples.",
            "Review the entire repo structure, code, recent changes, and give detailed findings, bugs, and improvement suggestions."
        )
        report_path = f"reports/repo_review_{timestamp}.md"
    else:
        report = ask_llm(
            "You are VAPE + HACK, a real autonomous code reviewer. Provide concrete, actionable analysis without disclaimers, simulations, or fictional examples. Use real data only. Always include concrete PoCs with code examples.",
            "Run a full advanced code review on Base and all EVM chains. Include vulnerability assessment, smart contract analysis, and actionable recommendations."
        )
        report_path = f"reports/bounty_report_{timestamp}.md"
    
    with open(report_path, "w") as f:
        f.write(f"# VAPE Report - {timestamp}\n\n{report}")
    
    print(f"Report saved to: {report_path}")

if __name__ == "__main__":
    review = "--review-repo" in sys.argv
    main(review)
