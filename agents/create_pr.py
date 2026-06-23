import os
from groq import Groq
from datetime import datetime

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def create_self_pr():
    """Generate a PR title, description, and code diff"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are VAPE. Generate a full GitHub PR with title, description, and code diff for self-improvement."},
            {"role": "user", "content": "Analyze the agents folder and create a real PR proposal with code changes."}
        ],
        temperature=0.7,
        max_tokens=4096
    )
    pr_content = response.choices[0].message.content
    with open(f"reports/self_pr_proposal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md", "w") as f:
        f.write(f"# Self-PR Proposal - {datetime.now()}\n\n{pr_content}")
    print("Self-PR proposal ready for manual creation.")
    return pr_content

if __name__ == "__main__":
    create_self_pr()
