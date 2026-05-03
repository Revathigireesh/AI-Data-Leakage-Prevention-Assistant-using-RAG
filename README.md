<div align="center">

```
██████╗  █████╗  ██████╗      ██████╗ ██╗     ██████╗
██╔══██╗██╔══██╗██╔════╝     ██╔══██╗██║     ██╔══██╗
██████╔╝███████║██║  ███╗    ██║  ██║██║     ██████╔╝
██╔══██╗██╔══██║██║   ██║    ██║  ██║██║     ██╔═══╝
██║  ██║██║  ██║╚██████╔╝    ██████╔╝███████╗██║
╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝     ╚═════╝ ╚══════╝╚═╝
```

# RAG Chatbot with Data Leakage Detection

**A beginner-friendly HR chatbot powered by local LLMs — with a built-in safety layer that blocks sensitive data before it reaches the model.**

[![Python](https://img.shields.io/badge/Python-3.10+-3776ab?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-ff4b4b?style=flat-square&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Ollama](https://img.shields.io/badge/Ollama-local_LLM-000000?style=flat-square)](https://ollama.com)
[![LangChain](https://img.shields.io/badge/LangChain-RAG-1c3c3c?style=flat-square)](https://langchain.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE)

</div>

---

## What this is

Employees often share sensitive data — passwords, salary figures, government IDs — while using AI tools, sometimes accidentally and sometimes through deliberate social engineering. This project is a learning exercise in building a chatbot that answers HR policy questions *and* catches risky inputs before they reach the LLM.

Everything runs locally. No data leaves your machine.

---

## How it works

```
User types a question
        │
        ▼
┌───────────────────┐
│   DLP Scanner     │  ◄── regex patterns for passwords, IDs,
│   (dlp_scanner)   │       salary, tokens, prompt injections
└────────┬──────────┘
         │
    Safe? ──── NO ──► Block input + show specific warning
         │
        YES
         │
         ▼
┌───────────────────┐
│   RAG Retrieval   │  ◄── embeds query → finds relevant
│   (rag_engine)    │       policy chunks from FAISS index
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│   Ollama LLM      │  ◄── llama3 / mistral running locally
│   (llm_connector) │
└────────┬──────────┘
         │
         ▼
     Answer shown in Streamlit UI
```

---

## DLP scanner — what it catches

| Category | Example inputs caught |
|---|---|
| 🔑 Password / credential | `password=abc123`, `my pwd is X`, `p@ssw0rd` |
| 💰 Salary / financial | `sal=85000`, `my ctc is 18lpa`, `salary=120000` |
| 🪪 Government ID | Aadhaar `1234 5678 9012`, PAN `ABCDE1234F` |
| 📱 Phone number | `9876543210`, `+91-9876543210` |
| 🏦 Bank / card details | Account numbers, Visa/Mastercard patterns |
| 🔐 API key / token | `sk-...`, `token=...`, JWT prefixes |
| 💉 Prompt injection | `ignore all instructions`, `jailbreak mode ON`, `system override` |

### Test results (100-query dataset)

```
Category       Blocked   Block rate
─────────────────────────────────────
Normal         0 / 15    ░░░░░░░░░░  0%   ✓ No false positives
Sensitive     15 / 15    ██████████ 100%  ✓ Perfect detection
Indirect       0 / 15    ░░░░░░░░░░  0%   ✓ Correctly passed through
Injection     11 / 15    ███████░░░  73%  ~ Some edge cases slip
Mixed          8 / 10    ████████░░  80%  ~ Good coverage
Edge cases     7 / 20    ███░░░░░░░  35%  △ Obfuscation is harder
```

---

## Project structure

```
rag_dlp_chatbot/
├── app.py                 ← Streamlit UI + pipeline orchestration
├── dlp_scanner.py         ← Regex-based DLP detection engine
├── rag_engine.py          ← Document loading, embedding, retrieval (FAISS)
├── llm_connector.py       ← Ollama LLM integration
├── test_dlp.py            ← Batch test script (100 queries)
├── requirements.txt       ← Python dependencies
└── data/
    └── company_policy.txt ← Knowledge base (leave, WFH, timings, etc.)
```

---

## Setup

### Step 1 — Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/rag-dlp-chatbot.git
cd rag-dlp-chatbot
```

### Step 2 — Install Python dependencies

```bash
pip install -r requirements.txt
```

> First run downloads a ~90MB sentence-transformer model for embeddings. This only happens once.

### Step 3 — Start Ollama and pull a model

```bash
# In a separate terminal
ollama serve

# Pick one
ollama pull llama3      # Recommended — 4.7 GB
ollama pull mistral     # Lighter — 4.1 GB
ollama pull phi3        # Smallest — 2.3 GB
```

If you use `mistral` or `phi3`, update `MODEL_NAME` in `llm_connector.py`.

### Step 4 — Run the chatbot

```bash
streamlit run app.py
```

Opens at **http://localhost:8501**

### Step 5 — Run the DLP test suite (optional, no Ollama needed)

```bash
python test_dlp.py
```

---

## Tech stack

| Tool | Purpose |
|---|---|
| **Streamlit** | Chat UI — input, history, sidebar stats |
| **Ollama** | Local LLM runner (llama3, mistral, phi3) |
| **LangChain** | Document loading, text splitting, RAG chain |
| **FAISS** | Vector store for fast similarity search |
| **sentence-transformers** | Local embeddings (all-MiniLM-L6-v2) |
| **Python `re`** | Regex-based DLP pattern matching |

---

## Known limitations

- The DLP scanner uses static regex — it won't catch every obfuscated input (e.g. base64-encoded instructions, HTML-entity-encoded passwords).
- Indirect fishing queries (e.g. "who earns the most?") pass through — they rely on the LLM refusing to answer, not the DLP layer.
- This is a learning project. It is not a substitute for a real enterprise DLP system.

**Good next steps:**
- Add an ML-based classifier for indirect/semantic threats
- Log all blocked queries for review
- Add a confidence score to the scanner output
- Expand the knowledge base with more policy documents

---

## License

MIT — use it, learn from it, break it, improve it.

---

<div align="center">
Built with Python · Ollama · LangChain · Streamlit<br>
All inference runs locally — your data stays on your machine.
</div>
