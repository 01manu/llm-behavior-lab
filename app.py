import glob
import pandas as pd
import streamlit as st

st.set_page_config(page_title="LLM Behavior Lab", page_icon="🔬", layout="wide")
st.title("🔬 LLM Behavior Lab")
st.caption("Same prompts, different models: what actually happens under the hood. "
           "Models: Gemini 3.5 Flash (Google) and gpt-oss-120b (open-weight, served by Groq).")


@st.cache_data  # read the files once, not on every click
def load(pattern):
    files = glob.glob(pattern)
    if not files:
        return pd.DataFrame()
    return pd.concat([pd.read_csv(f) for f in files], ignore_index=True)


exp1 = load("results/exp1_nondeterminism.csv")
needle = load("results/exp2a_needle_*.csv")
outlimit = load("results/exp2b_output_limit_*.csv")

tab1, tab2, tab3, tab4 = st.tabs(["1 · Non-determinism", "2 · Context limits",
                                  "3 · Output limit", "🛠 Support playbook"])

# ---------------- Tab 1: non-determinism ----------------
with tab1:
    st.subheader("Does temperature 0 give the same answer every time?")
    st.write("Prompt: *Suggest one name for a new coffee shop in Berlin.* 5 runs per model and temperature.")
    if exp1.empty:
        st.info("No data yet. Run exp1_nondeterminism.py first.")
    else:
        ok = exp1[exp1["answer"].notna()].copy()
        ok["temperature"] = ok["temperature"].astype(str)
        summary = (ok.groupby(["model", "temperature"])
                     .agg(unique_answers=("answer", "nunique"),
                          median_seconds=("seconds", "median"),
                          avg_thinking_tokens=("thinking_tokens", "mean"),
                          input_tokens=("input_tokens", "first"))
                     .reset_index())

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Different answers out of 5**")
            st.bar_chart(summary, x="temperature", y="unique_answers", color="model", stack=False)
        with c2:
            st.markdown("**Median latency (seconds)**")
            st.bar_chart(summary, x="temperature", y="median_seconds", color="model", stack=False)

        st.markdown("**Summary**")
        st.dataframe(summary.round(1), hide_index=True, use_container_width=True)

        st.markdown("**Every answer, run by run**")
        answers = ok.pivot_table(index="run", columns=["model", "temperature"],
                                 values="answer", aggfunc="first")
        answers.columns = [f"{m} · temp {t}" for m, t in answers.columns]
        st.dataframe(answers, use_container_width=True)

        st.success("Finding: temperature 0 made gpt-oss fully consistent (5/5 identical) but not Gemini "
                   "(4 different answers). Gemini's hidden reasoning varied between runs, which changed the answer.")

# ---------------- Tab 2: context limits ----------------
with tab2:
    st.subheader("Can the model find one hidden fact in a long document?")
    st.write("A Wi-Fi password hidden at 10% / 50% / 90% of a generated handbook of ~2k / ~7.5k / ~30k tokens.")
    if needle.empty:
        st.info("No data yet. Run exp2_context_limits.py first.")
    else:
        needle["error"] = needle["error"].fillna("").astype(str)

        def label(row):
            if row["found"] is True or str(row["found"]) == "True":
                return "✅ found"
            e = row["error"]
            if "413" in e:
                return "⛔ 413 too large (plan limit)"
            if "503" in e:
                return "⚠️ 503 provider overloaded"
            if "429" in e:
                return "⏳ 429 quota exceeded"
            if e:
                return "🔌 other error"
            return "❌ wrong answer"

        needle["result"] = needle.apply(label, axis=1)
        needle["position"] = needle["needle_position"].map({0.1: "start (10%)", 0.5: "middle (50%)",
                                                           0.9: "end (90%)"})

        cols = st.columns(len(needle["model"].unique()))
        for col, model in zip(cols, sorted(needle["model"].unique())):
            with col:
                st.markdown(f"**{model}**")
                grid = needle[needle["model"] == model].pivot_table(
                    index="doc_words", columns="position", values="result", aggfunc="first")
                grid.index = [f"{w:,} words" for w in grid.index]
                st.dataframe(grid, use_container_width=True)

        st.markdown("**Latency grows with document size** (successful requests, median seconds)")
        lat = (needle[needle["result"] == "✅ found"]
               .groupby(["doc_words", "model"])["seconds"].median().reset_index())
        lat["doc_words"] = lat["doc_words"].astype(str)
        st.bar_chart(lat, x="doc_words", y="seconds", color="model", stack=False)

        st.success("Finding: whenever a model received the whole document, it found the fact at every position. "
                   "All failures came from limits or infrastructure: Groq's free tier allows 8,000 tokens per minute, "
                   "so a 29k-token request was rejected (413); Gemini was sometimes overloaded (503).")

# ---------------- Tab 3: output limit ----------------
with tab3:
    st.subheader("What happens when the answer is longer than max_tokens?")
    st.write("Task: *Explain how the Berlin Wall fell, at least 300 words*, with max_tokens = 100.")
    if outlimit.empty:
        st.info("No data yet.")
    else:
        show = outlimit[[c for c in ["model", "finish_reason", "answer_words", "output_tokens",
                                     "thinking_tokens", "error"] if c in outlimit.columns]]
        st.dataframe(show, hide_index=True, use_container_width=True)
        for _, r in outlimit[outlimit["answer"].notna()].iterrows():
            with st.expander(f"Answer from {r['model']} (cut off)"):
                st.write(r["answer"])
        st.success("Finding: the answer stopped mid-sentence (finish_reason = length). For reasoning models, "
                   "hidden thinking uses part of the same token budget, so even less visible text fits.")

# ---------------- Tab 4: support playbook ----------------
with tab4:
    st.subheader("Debugging \"the AI isn't working\": check how far the request got")
    st.markdown("""
| Signal | Layer | What it means | What to do |
|---|---|---|---|
| `getaddrinfo failed` / connection error | Network (user side) | Request never reached the provider | Check internet, VPN, proxy, firewall |
| **503** Unavailable | Provider | Servers overloaded, temporary | Retry with exponential backoff |
| **429** Resource exhausted | Account | Quota or rate limit reached | Wait, slow down, or upgrade plan |
| **413** Request too large | Plan / input size | Input exceeds the plan's limit (not necessarily the model's) | Shorten or split the document, or upgrade |
| `finish_reason = length` | Configuration | Answer hit max_tokens | Raise max_tokens, especially for reasoning models |
| Success, but wrong answer | Model behavior | The model did something unexpected | Compare models, adjust prompt, check context |
""")
    st.caption("Every row in this table came up in my own experiments.")

st.divider()
st.caption("Built by Manoj Shravanagere Eranna · github.com/01manu/llm-behavior-lab")