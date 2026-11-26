import os, time, csv, random
from dotenv import load_dotenv
from google import genai
from google.genai import types
from groq import Groq

load_dotenv()
gemini = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
groq = Groq(api_key=os.getenv("GROQ_API_KEY"))

GEMINI_MODEL = "gemini-3.5-flash"
GROQ_MODEL = "openai/gpt-oss-120b"

# >>> Choose which models to run. Result files are named after them automatically. <<<
RUN = ["gemini-3.5-flash", "gpt-oss-120b"]       # full experiment: ["gemini-3.5-flash", "gpt-oss-120b"]

# ---------- Part A setup: a fake handbook with a hidden fact ----------
NEEDLE = "Note for staff: the Wi-Fi password for the Berlin office is BLAUER-ELEFANT-42."
QUESTION = "What is the Wi-Fi password for the Berlin office? Reply with the password only."
EXPECTED = "BLAUER-ELEFANT-42"
SIZES_WORDS = [1500, 6000, 24000]      # roughly 2k, 8k and 30k tokens
POSITIONS = [0.1, 0.5, 0.9]            # start, middle, end

random.seed(42)  # same "random" handbook every run, so results are reproducible
TOPICS = ["travel expenses", "holiday requests", "laptop setup", "parking", "meeting rooms",
          "security badges", "printer use", "lunch breaks", "remote work", "onboarding"]
DEPTS = ["HR", "IT", "Finance", "Facilities", "Legal"]
TEMPLATES = [
    "Employees must submit {t} forms before the {n}th of each month.",
    "Questions about {t} should be sent to the {d} team.",
    "The policy on {t} was last updated in {y}.",
    "For {t}, managers approve requests within {n} working days.",
    "Exceptions to the {t} rules require written approval from {d}.",
]

def build_document(n_words, position):
    sentences, count = [], 0
    while count < n_words:
        s = random.choice(TEMPLATES).format(t=random.choice(TOPICS), n=random.randint(2, 28),
                                            d=random.choice(DEPTS), y=random.randint(2015, 2025))
        sentences.append(s)
        count += len(s.split())
    sentences.insert(int(len(sentences) * position), NEEDLE)
    return " ".join(sentences)

# ---------- Model calls ----------
def ask_gemini(prompt, max_tokens=None):
    cfg = types.GenerateContentConfig(max_output_tokens=max_tokens) if max_tokens else None
    start = time.perf_counter()
    r = gemini.models.generate_content(model=GEMINI_MODEL, contents=prompt, config=cfg)
    u = r.usage_metadata
    return {"answer": (r.text or "").strip(), "seconds": round(time.perf_counter() - start, 2),
            "input_tokens": u.prompt_token_count, "output_tokens": u.candidates_token_count,
            "thinking_tokens": u.thoughts_token_count or 0,
            "finish_reason": str(r.candidates[0].finish_reason)}

def ask_gptoss(prompt, max_tokens=None):
    extra = {"max_completion_tokens": max_tokens} if max_tokens else {}
    start = time.perf_counter()
    r = groq.chat.completions.create(model=GROQ_MODEL,
                                     messages=[{"role": "user", "content": prompt}], **extra)
    u = r.usage
    return {"answer": (r.choices[0].message.content or "").strip(),
            "seconds": round(time.perf_counter() - start, 2),
            "input_tokens": u.prompt_tokens, "output_tokens": u.completion_tokens,
            "thinking_tokens": "", "finish_reason": r.choices[0].finish_reason}

ALL_MODELS = {"gemini-3.5-flash": ask_gemini, "gpt-oss-120b": ask_gptoss}
MODELS = {name: ALL_MODELS[name] for name in RUN}
TAG = "_".join(RUN).replace(".", "")

EMPTY = {"answer": "", "seconds": "", "input_tokens": "", "output_tokens": "",
         "thinking_tokens": "", "finish_reason": ""}

def safe_call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs), ""
    except Exception as e:
        return dict(EMPTY), str(e)[:500]

TEMPORARY_ERRORS = ("503", "429", "getaddrinfo", "timed out", "Connection")

def call_with_retry(fn, *args, retries=4, **kwargs):
    wait = 5
    for attempt in range(1, retries + 1):
        res, err = safe_call(fn, *args, **kwargs)
        if not err:
            return res, ""
        if not any(code in err for code in TEMPORARY_ERRORS):  # e.g. 413 or 400: retrying won't help
            return res, err
        print(f"   attempt {attempt} failed ({err[:30]}...), retrying in {wait}s")
        time.sleep(wait)
        wait *= 2  # 5s, 10s, 20s, 40s
    return res, err

def save(rows, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"Saved: {path}")

os.makedirs("results", exist_ok=True)

# ---------- Part A: needle in a haystack ----------
print("=== PART A: needle in a haystack ===")
rows_a = []
for size in SIZES_WORDS:
    for pos in POSITIONS:
        doc = build_document(size, pos)
        prompt = f"Here is our company handbook:\n\n{doc}\n\n{QUESTION}"
        for name, fn in MODELS.items():
            res, err = call_with_retry(fn, prompt)
            found = EXPECTED in res["answer"].upper()
            rows_a.append({"model": name, "doc_words": size, "needle_position": pos,
                           **res, "found": found, "error": err})
            status = "✅ found" if found else (f"❌ ERROR: {err[:80]}" if err else f"❌ answered: {res['answer'][:60]}")
            print(f"{name:17} | {size:>6} words | pos {pos} | in_tokens={res['input_tokens']} | {status}")
            time.sleep(6)
save(rows_a, f"results/exp2a_needle_{TAG}.csv")

# ---------- Part B: output limit ----------
print("\n=== PART B: output limit (max 100 tokens) ===")
LONG_TASK = "Explain in detail how the Berlin Wall fell in 1989. Write at least 300 words."
rows_b = []
for name, fn in MODELS.items():
    res, err = call_with_retry(fn, LONG_TASK, max_tokens=100)
    words = len(res["answer"].split())
    rows_b.append({"model": name, "max_tokens": 100, **res, "answer_words": words, "error": err})
    print(f"{name:17} | finish_reason={res['finish_reason']} | visible words={words} | "
          f"output_tokens={res['output_tokens']} | thinking={res['thinking_tokens']} | {err[:80]}")
    time.sleep(6)
save(rows_b, f"results/exp2b_output_limit_{TAG}.csv")