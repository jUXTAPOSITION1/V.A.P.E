from groq import Groq
from datetime import datetime

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def red_team_test(target):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a professional red teamer. Be technical and concrete."},
            {"role": "user", "content": f"Perform advanced red teaming on {target}. Include prompt injection, jailbreak, and agent workflow attacks."}
        ],
        temperature=0.8,
        max_tokens=2048
    )
    return response.choices[0].message.content

def main_redteam():
    report = red_team_test("Base and Virtuals protocols")
    with open(f"reports/redteam_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md", "w") as f:
        f.write(f"# Red Team Report - {datetime.now()}\n\n{report}")
    print("Red team report generated.")

if __name__ == "__main__":
    main_redteam()
