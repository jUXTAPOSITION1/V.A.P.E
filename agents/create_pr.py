import os
import requests
from groq import Groq
from datetime import datetime

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
GITHUB_TOKEN = os.getenv("Vape_agent_token")
REPO = "jUXTAPOSITION1/V.A.P.E"

def create_github_pr(title, body, branch_name):
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    data = {"title": title, "body": body, "head": branch_name, "base": "main"}
    response = requests.post(f"https://api.github.com/repos/{REPO}/pulls", headers=headers, json=data)
    print("PR created:", response.json().get("html_url", response.text))
    return response.json()

def propose_and_create_pr():
    """VAPE proposes and creates a real PR"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are VAPE. Generate a real PR title, description, and code diff for self-improvement."},
            {"role": "user", "content": "Analyze the agents folder and create a real PR proposal with code changes."}
        ],
        temperature=0.7,
        max_tokens=4096
    )
    pr_content = response.choices[0].message.content
    title = "VAPE Self-Improvement: " + pr_content.split("\n")[0][:100]
    body = pr_content
    branch_name = f"vape-improvement-{datetime.now().strftime('%Y%m%d')}"
    
    create_github_pr(title, body, branch_name)
    return pr_content

if __name__ == "__main__":
    propose_and_create_pr()
