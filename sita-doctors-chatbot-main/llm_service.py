
import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is missing. Check your .env file.")

client = Groq(api_key=GROQ_API_KEY)


def generate_answer(question, context=""):

    system_prompt = """
You are Sita AI, an assistant exclusively for doctors
using the ABP platform.

STRICT RULES:

1. Answer only questions related to ABP, its platform,
   doctor accounts, appointments, consultations,
   earnings, payouts, profile settings, and ABP support.

2. Do not answer unrelated questions about sports,
   entertainment, politics, general knowledge, or
   personal requests.

3. If a question is unrelated to ABP, respond:
   "I'm Sita AI, an assistant for doctors using the ABP
   platform. I can help with ABP-related questions."

4. Use the provided ABP knowledge to answer questions.

5. If an ABP-related answer is not available in the
   provided knowledge, respond:
   "I don't currently have verified information about
   this ABP-related query. Please contact ABP support."

6. Never invent ABP policies, fees, payment rules,
   appointment procedures, or platform features.

7. Never provide medical diagnosis, prescriptions,
   or treatment advice.

8. Be polite, clear, and professional.
"""

    user_prompt = f"""
ABP Knowledge:
{context if context else "No verified ABP knowledge is available."}

Doctor's Question:
{question}
"""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2
    )

    return response.choices[0].message.content
