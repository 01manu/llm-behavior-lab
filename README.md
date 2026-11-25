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