import os, time, csv
from collections import defaultdict
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types
from groq import Groq

load_dotenv()
gemini = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
groq = Groq(api_key=os.getenv("GROQ_API_KEY"))

PROMPT = "Suggest one name for a new coffee shop in Berlin. Reply with the name only."
TEMPERATURES = [0.0, 1.0]
RUNS = 5


def ask_gemini(prompt, temperature):
    start = time.perf_counter()
    r = gemini.models.generate_content(
        model="gemini-3.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(temperature=temperature),
    )
    seconds = time.perf_counter() - start
    u = r.usage_metadata
    return {
        "answer": (r.text or "").strip(),
        "seconds": round(seconds, 2),
        "input_tokens": u.prompt_token_count,
        "output_tokens": u.candidates_token_count,
        "thinking_tokens": u.thoughts_token_count or 0,
    }


def ask_gptoss(prompt, temperature):
    start = time.perf_counter()
    r = groq.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    seconds = time.perf_counter() - start
    u = r.usage
    return {
        "answer": (r.choices[0].message.content or "").strip(),
        "seconds": round(seconds, 2),
        "input_tokens": u.prompt_tokens,
        "output_tokens": u.completion_tokens,   # includes hidden reasoning tokens
        "thinking_tokens": "",                  # not reported separately
    }


MODELS = {"gemini-3.5-flash": ask_gemini, "gpt-oss-120b": ask_gptoss}

os.makedirs("results", exist_ok=True)
rows = []

for model_name, ask in MODELS.items():
    for temp in TEMPERATURES:
        for run in range(1, RUNS + 1):
            try:
                result = ask(PROMPT, temp)
                error = ""
            except Exception as e:  # log errors instead of crashing (e.g. 429 rate limit)
                result = {"answer": "", "seconds": "", "input_tokens": "",
                          "output_tokens": "", "thinking_tokens": ""}
                error = str(e)[:200]
            rows.append({"time": datetime.now().isoformat(timespec="seconds"),
                         "model": model_name, "temperature": temp, "run": run,
                         **result, "error": error})
            print(f"{model_name} | temp={temp} | run {run}: {result['answer'] or 'ERROR: ' + error}")
            time.sleep(4)  # stay under free-tier rate limits

with open("results/exp1_nondeterminism.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

# Summary: how many different answers per model and temperature?
print("\n=== SUMMARY ===")
groups = defaultdict(list)
for r in rows:
    if r["answer"]:
        groups[(r["model"], r["temperature"])].append(r)
for (model, temp), items in groups.items():
    unique = len(set(i["answer"] for i in items))
    avg_s = sum(i["seconds"] for i in items) / len(items)
    print(f"{model:18} temp={temp}: {unique} unique answers out of {len(items)} | avg {avg_s:.2f}s")