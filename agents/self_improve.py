import os
from groq import Groq
from datetime import datetime

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def self_review_and_improve():
    """VAPE reviews its own code and suggests improvements"""
    code_context = "Review the agents folder and suggest concrete code improvements, new features, and bug fixes for better bug bounty performance."
    improvement_plan = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are VAPE. Analyze your own code and propose specific improvements. Be concrete."},
            {"role": "user", "content": code_context}
        ],
        temperature=0.7,
        max_tokens=2048
    ).choices[0].message.content

    report = f"# Self-Improvement Report - {datetime.now()}\n\n{improvement_plan}"
    with open("reports/self_improve_{datetime.now().strftime('%Y%m%d')}.md", "w") as f:
        f.write(report)
    
    print("Self-improvement analysis complete. See reports/")
    return improvement_plan

if __name__ == "__main__":
    self_review_and_improve()
