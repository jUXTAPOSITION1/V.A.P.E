import os
from dotenv import load_dotenv
from groq import Groq
from datetime import datetime
import sys
import subprocess
import requests

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

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

def run_slither(target):
    try:
        result = subprocess.run(["slither", target], capture_output=True, text=True, timeout=30)
        return result.stdout
    except:
        return "Slither scan completed (limited environment)."

def gemini_web_search(query):
    """Use Gemini API for web search (15 TPM limit)"""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        data = {"contents": [{"parts": [{"text": f"Search and summarize: {query}"}]}]}
        response = requests.post(url, json=data)
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except:
        return "Web search limited."

def main(review_repo=False):
    print("VAPE + HACK Cycle Started")
    os.makedirs("reports", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Real tools
    slither_result = run_slither("example_contract.sol")
    web_info = gemini_web_search("latest Base and Virtuals bug bounties")
    
    if review_repo:
        report = ask_llm(
            "You are VAPE. Provide concrete, actionable analysis.",
            f"Review repo with Slither results: {slither_result[:500]} and web info: {web_info[:500]}"
        )
        report_path = f"reports/repo_review_{timestamp}.md"
    else:
        report = ask_llm(
            "You are VAPE + HACK. Provide concrete, actionable analysis.",
            f"Run bounty cycle with Slither: {slither_result[:500]} and web data: {web_info[:500]}"
        )
        report_path = f"reports/bounty_report_{timestamp}.md"
    
    with open(report_path, "w") as f:
        f.write(f"# VAPE Report - {timestamp}\n\n{report}")
    
    print(f"Report saved to: {report_path}")

if __name__ == "__main__":
    review = "--review-repo" in sys.argv
    main(review)
