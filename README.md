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

## Findings
Coming soon. Each finding is written in plain language: what happened, and why.