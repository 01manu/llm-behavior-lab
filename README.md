# LLM Behavior Lab
Why does the same prompt give different answers? Why do long documents get cut off?
Why does one model call the wrong tool? This project tests these questions
by sending identical prompts to models from different providers and comparing the results.

## Experiments
| # | Experiment | Status |
|---|---|---|
| 1 | Non-determinism (same prompt, repeated runs, different temperatures) | 🔄 In progress |
| 2 | Context limits (a fact hidden at the end of a long document) | ⏳ Planned |
| 3 | Prompt sensitivity and system prompts | ⏳ Planned |
| 4 | Tool calling | ⏳ Planned |
| 5 | Latency, tokens and cost | ⏳ Planned |
| 6 | Hallucination on made-up facts | ⏳ Planned |

## Models
Google Gemini (Flash) · Meta Llama (via Groq)

## Finding 1: Temperature 0 is not the same as "deterministic"
**Setup:** Same prompt ("Suggest one name for a new coffee shop in Berlin"), 5 runs each
at temperature 0 and 1.0. Models: Gemini 3.5 Flash, gpt-oss-120b (via Groq). Data: `results/exp1_nondeterminism.csv`

| | Gemini 3.5 Flash | gpt-oss-120b |
|---|---|---|
| Unique answers at temp 0 | 4 / 5 | 1 / 5 |
| Unique answers at temp 1.0 | 5 / 5 | 3 / 5 |
| Median latency | ~3.8 s | ~0.46 s |
| Input tokens for the same prompt | 18 | 88 |
| Hidden reasoning tokens | 409–748 per run (~99% of output) | included in output, 68–86 |

**What I learned**
- Temperature 0 made gpt-oss fully consistent (identical answer and identical token count in 5/5 runs),
  but not Gemini. Gemini's hidden thinking varied from 409 to 748 tokens per run, so it reasoned differently
  each time, which led to different answers.
- Hidden reasoning dominates cost: Gemini used ~100 thinking tokens per visible answer token.
- The same prompt counted as 18 vs 88 input tokens, because gpt-oss adds a chat template and system instructions.
- One Gemini request took 49 s instead of ~4 s. Averages hide outliers like this, so I report medians.

**Limits:** 5 runs per setting is a small sample; these are observations, not general rules.

## Finding 2: "The AI ignored my document" has several different causes
**Setup:** A generated company handbook (seeded for reproducibility) with one hidden fact (a Wi-Fi password),
placed at 10% / 50% / 90% of the text, at ~2k / ~7.5k / ~30k tokens. Part B: a 300-word task with max_tokens=100.
Data: `results/exp2a_needle*.csv`, `results/exp2b_output_limit*.csv`

| Size | Gemini 3.5 Flash | gpt-oss-120b (Groq free tier) |
|---|---|---|
| ~2k tokens | ✅ 3/3 found | ✅ 3/3 found |
| ~7.5k tokens | ✅ 3/3 found | ✅ 3/3 found |
| ~30k tokens | ✅ 1/1 found, 2 runs failed with 503 (provider overloaded) | ❌ 413 Request too large (free-tier limit: [LIMIT] tokens, requested: [REQUESTED]) |

**What I learned**
- Whenever a model received the full document, it found the fact, at every position. No "lost in the middle" effect up to ~30k tokens.
- Every failure came from limits or infrastructure, not from the models' reading:
  - **413:** the request exceeded Groq's free-tier limit. The model itself supports much more; the limit came from the plan.
  - **503:** Gemini's servers were overloaded. Retrying with exponential backoff recovered one request.
  - **429:** my free-tier quota was used up. One retry after 5 s succeeded.
  - **Network error (DNS):** the request never left my laptop.
- **Output limit:** with max_tokens=100, gpt-oss stopped mid-answer after 52 words (`finish_reason=length`);
  about 30 of the 100 tokens went to hidden reasoning.
- **Latency grows with input size:** Gemini took ~2–4 s at 2k tokens but ~18 s at 30k, for the same 10-token answer.
- **Tokenizers differ:** the same 6,000-word text counted as ~7,690 tokens for Gemini vs ~7,370 for gpt-oss,
  so "price per token" is not directly comparable across providers.

**Support takeaway:** When a user says "the AI ignored my document", first check how far the request got:
network → provider (503) → account limits (429) → plan or input size (413) → output limit (`finish_reason`)
→ only then model behavior.

**Limits:** Small sample; the 503s at 30k tokens could be bad timing or size-related, and I can't tell yet.