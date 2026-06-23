import os
from dotenv import load_dotenv
from datetime import datetime
from groq import Groq

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
        max_tokens=2048
    )
    return response.choices[0].message.content

def main():
    print("VAPE + HACK Autonomous Bug Bounty Cycle Started")
    
    os.makedirs("reports", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Use real LLM
    report = ask_llm(
        "You are VAPE + HACK, a powerful bug bounty agent.",
        "Run a full bounty cycle on Base and Virtuals protocols. Generate a detailed report."
    )
    
    report_path = f"reports/bounty_report_{timestamp}.md"
    with open(report_path, "w") as f:
        f.write(f"# VAPE + HACK Report - {timestamp}\n\n{report}")
    
    print(f"Real LLM Report generated and saved to: {report_path}")
    print("Cycle complete.")

if __name__ == "__main__":
    main()
