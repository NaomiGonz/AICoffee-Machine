# llm/gpt_handler.py

from openai import OpenAI

# ✅ Hardcoded API Key — be cautious with this in production
client = OpenAI(api_key="")

def call_gpt_4o(system_prompt: str, user_prompt: str) -> str:
    """
    Calls OpenAI's GPT-4o model with the provided system and user prompts.
    Logs the entire exchange and returns the model's textual response.
    """
    print("📡 Sending to GPT-4o:")
    print("🔒 System Prompt:\n", system_prompt)
    print("🗣️ User Prompt:\n", user_prompt)

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
        )
        content = response.choices[0].message.content.strip()
        print("📬 GPT Response:\n", content)
        return content
    except Exception as e:
        print("❌ GPT API Error:", str(e))
        return None
