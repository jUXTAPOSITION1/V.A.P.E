from groq import Groq
from datetime import datetime

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def propose_pr():
    """VAPE analyzes its own code and proposes a PR with code changes"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are VAPE. Propose a concrete GitHub PR with actual code diffs for self-improvement."},
            {"role": "user", "content": "Analyze the agents folder and propose a specific improvement as a PR with code diffs."}
        ],
        temperature=0.7,
        max_tokens=4096
    )
    pr_plan = response.choices[0].message.content
    with open(f"reports/self_pr_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md", "w") as f:
        f.write(f"# Proposed Self-PR - {datetime.now()}\n\n{pr_plan}")
    print("Self-PR proposal generated.")
    return pr_plan

if __name__ == "__main__":
    propose_pr()
