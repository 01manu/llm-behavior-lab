import os
from dotenv import load_dotenv
from google import genai
from groq import Groq

load_dotenv()  # reads the keys from .env

gemini = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
groq = Groq(api_key=os.getenv("GROQ_API_KEY"))

# 1) Which models can I use? (names change often, so we look them up)
print("Gemini models:")
for m in gemini.models.list():
    print("  ", m.name)

print("\nGroq models:")
for m in groq.models.list().data:
    print("  ", m.id)

# 2) Send the same question to both
prompt = "In one sentence: why is the sky blue?"

g = gemini.models.generate_content(model="gemini-3.5-flash", contents=prompt)
print("\nGemini:", g.text)

r = groq.chat.completions.create(
    model="openai/gpt-oss-120b",
    messages=[{"role": "user", "content": prompt}],
)
print("Llama:", r.choices[0].message.content)
print("gpt-oss tokens:",
      "input =", r.usage.prompt_tokens,
      "| output =", r.usage.completion_tokens,
      "| total =", r.usage.total_tokens)