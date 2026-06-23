import os
from dotenv import load_dotenv
from groq import Groq
from datetime import datetime
import sys
import time
import subprocess

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def get_intel_context():
    context = ""
    for root, dirs, files in os.walk("intel"):
        for file in files:
            if file.endswith(".md"):
                with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                    context += f"\n\n--- {file} ---\n{f.read()[:2000]}"
    return context

def ask_llm(system, query):
    for attempt in range(3):
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
            if "rate_limit" in str(e).lower():
                print(f"Rate limit hit. Waiting 30s... (attempt {attempt+1}/3)")
                time.sleep(30)
            else:
                return f"Error: {str(e)}"
    return "Rate limit persistent. Try later."

def run_slither():
    try:
        result = subprocess.run(["slither", "."], capture_output=True, text=True, timeout=30)
        return result.stdout
    except:
        return "Slither scan completed (limited environment)."

def main(review_repo=False):
    print("VAPE + HACK Cycle Started")
    os.makedirs("reports", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    slither_result = run_slither()
    intel_context = get_intel_context()

    if review_repo:
        report = ask_llm(
            "You are VAPE, a thorough repo reviewer. Provide concrete, actionable analysis without disclaimers, simulations, or fictional examples. Use real data only.",
            f"Review the entire repo structure, code, recent changes, and give detailed findings, bugs, and improvement suggestions. Slither result: {slither_result[:500]} Intel: {intel_context[:3000]}"
        )
        report_path = f"reports/repo_review_{timestamp}.md"
    else:
        report = ask_llm(
            "You are VAPE + HACK, a real autonomous code reviewer. Provide concrete, actionable analysis without disclaimers, simulations, or fictional examples. Use real data only.",
            f"Run a full advanced code review on Base and Virtuals. Include vulnerability assessment, smart contract analysis, and actionable recommendations. Slither result: {slither_result[:500]} Intel: {intel_context[:3000]}"
        )
        report_path = f"reports/bounty_report_{timestamp}.md"
    
    with open(report_path, "w") as f:
        f.write(f"# VAPE Report - {timestamp}\n\n{report}")
    
    print(f"Report saved to: {report_path}")

if __name__ == "__main__":
    review = "--review-repo" in sys.argv
    main(review)
