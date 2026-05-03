"""
app.py
------
Main Streamlit application.
Orchestrates the full pipeline:
  User input → DLP Scanner → RAG retrieval → Ollama LLM → Response

Run with:
    streamlit run app.py
"""

import streamlit as st
import time

from dlp_scanner import scan, get_category_label
from rag_engine import build_vectorstore, retrieve_context
from retrieval.llm_connector import ask_ollama, check_ollama_running


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Company HR Chatbot",
    page_icon="🏢",
    layout="centered",
)


# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------

st.markdown("""
<style>
    /* Main container */
    .main .block-container { max-width: 780px; padding-top: 2rem; }

    /* Header */
    .app-header {
        background: #1e293b;
        color: white;
        padding: 1.2rem 1.5rem;
        border-radius: 10px;
        margin-bottom: 1.5rem;
    }
    .app-header h1 { color: white; font-size: 1.4rem; margin: 0; font-weight: 600; }
    .app-header p { color: #94a3b8; font-size: 0.85rem; margin: 4px 0 0; }

    /* Chat messages */
    .chat-user {
        background: #eff6ff;
        border-left: 3px solid #3b82f6;
        padding: 0.8rem 1rem;
        border-radius: 0 8px 8px 0;
        margin: 0.5rem 0;
        font-size: 0.95rem;
    }
    .chat-bot {
        background: #f0fdf4;
        border-left: 3px solid #22c55e;
        padding: 0.8rem 1rem;
        border-radius: 0 8px 8px 0;
        margin: 0.5rem 0;
        font-size: 0.95rem;
    }
    .chat-blocked {
        background: #fef2f2;
        border-left: 3px solid #ef4444;
        padding: 0.8rem 1rem;
        border-radius: 0 8px 8px 0;
        margin: 0.5rem 0;
        font-size: 0.95rem;
    }

    /* DLP badge */
    .dlp-badge {
        display: inline-block;
        background: #fee2e2;
        color: #991b1b;
        font-size: 0.7rem;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 12px;
        margin-bottom: 6px;
        letter-spacing: 0.03em;
    }

    /* Status bar */
    .status-bar {
        display: flex;
        gap: 12px;
        font-size: 0.78rem;
        color: #64748b;
        margin-bottom: 1rem;
        padding: 8px 12px;
        background: #f8fafc;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
    }
    .status-dot-green { color: #22c55e; }
    .status-dot-red { color: #ef4444; }

    /* Input area */
    .stTextInput > div > div > input {
        border-radius: 8px;
        border: 1.5px solid #cbd5e1;
        font-size: 0.95rem;
    }

    /* Stats sidebar */
    .stat-box {
        background: #f1f5f9;
        border-radius: 8px;
        padding: 10px 14px;
        margin-bottom: 8px;
        font-size: 0.85rem;
    }
    .stat-box .num { font-size: 1.4rem; font-weight: 700; color: #1e293b; }
    .stat-box .lbl { color: #64748b; font-size: 0.75rem; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

if "stats" not in st.session_state:
    st.session_state.stats = {
        "total": 0,
        "answered": 0,
        "blocked": 0,
        "categories": {},
    }

if "vectorstore_ready" not in st.session_state:
    st.session_state.vectorstore_ready = False


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown("""
<div class="app-header">
    <h1>🏢 Company HR Chatbot</h1>
    <p>Ask about leave policy, WFH, office timings, and more &nbsp;·&nbsp; Sensitive data is automatically blocked</p>
</div>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sidebar — status and stats
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### System status")

    ollama_ok = check_ollama_running()
    ollama_status = "🟢 Ollama running" if ollama_ok else "🔴 Ollama offline"
    rag_status = "🟢 Knowledge base ready" if st.session_state.vectorstore_ready else "🟡 Loading..."

    st.markdown(f"""
    <div class="status-bar" style="flex-direction:column; gap:4px;">
        <span>{ollama_status}</span>
        <span>{rag_status}</span>
    </div>
    """, unsafe_allow_html=True)

    if not ollama_ok:
        st.warning("Start Ollama in your terminal:\n```\nollama serve\n```\nThen pull a model:\n```\nollama pull llama3\n```")

    st.markdown("---")
    st.markdown("### Session stats")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""<div class="stat-box">
            <div class="num">{st.session_state.stats['total']}</div>
            <div class="lbl">Total queries</div></div>""", unsafe_allow_html=True)
        st.markdown(f"""<div class="stat-box">
            <div class="num" style="color:#22c55e">{st.session_state.stats['answered']}</div>
            <div class="lbl">Answered</div></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="stat-box">
            <div class="num" style="color:#ef4444">{st.session_state.stats['blocked']}</div>
            <div class="lbl">Blocked</div></div>""", unsafe_allow_html=True)

    if st.session_state.stats["categories"]:
        st.markdown("**Blocked by category:**")
        for cat, count in st.session_state.stats["categories"].items():
            st.markdown(f"- {cat}: **{count}**")

    st.markdown("---")
    st.markdown("### Try these queries")
    example_queries = [
        "How many casual leaves do we get?",
        "Can I WFH on Fridays?",
        "What are the office timings?",
        "How do I claim travel reimbursement?",
        "What documents are needed for onboarding?",
    ]
    for q in example_queries:
        if st.button(q, key=f"ex_{q[:20]}", use_container_width=True):
            st.session_state["prefill"] = q

    st.markdown("---")
    if st.button("Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.stats = {"total": 0, "answered": 0, "blocked": 0, "categories": {}}
        st.rerun()


# ---------------------------------------------------------------------------
# Load vectorstore on first run
# ---------------------------------------------------------------------------

if not st.session_state.vectorstore_ready:
    with st.spinner("Loading company knowledge base..."):
        try:
            build_vectorstore()
            st.session_state.vectorstore_ready = True
        except Exception as e:
            st.error(f"Failed to load knowledge base: {e}")


# ---------------------------------------------------------------------------
# Chat history display
# ---------------------------------------------------------------------------

for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f'<div class="chat-user"><b>You:</b> {msg["content"]}</div>', unsafe_allow_html=True)
    elif msg["role"] == "assistant":
        st.markdown(f'<div class="chat-bot"><b>HR Assistant:</b> {msg["content"]}</div>', unsafe_allow_html=True)
    elif msg["role"] == "blocked":
        cat_label = msg.get("category_label", "Sensitive data")
        st.markdown(f"""
        <div class="chat-blocked">
            <div class="dlp-badge">BLOCKED &nbsp;·&nbsp; {cat_label}</div><br>
            <b>Security notice:</b> {msg["content"]}
        </div>""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# User input
# ---------------------------------------------------------------------------

prefill = st.session_state.pop("prefill", "")

with st.form(key="chat_form", clear_on_submit=True):
    user_input = st.text_input(
        label="Your question",
        value=prefill,
        placeholder="e.g. How many leaves do I get per year?",
        label_visibility="collapsed",
    )
    submitted = st.form_submit_button("Send →", use_container_width=True)


# ---------------------------------------------------------------------------
# Pipeline execution
# ---------------------------------------------------------------------------

if submitted and user_input.strip():
    query = user_input.strip()
    st.session_state.stats["total"] += 1

    # --- Step 1: DLP scan ---
    scan_result = scan(query)

    if not scan_result.is_safe:
        # Blocked — do not pass to RAG or LLM
        cat_label = get_category_label(scan_result.category)
        st.session_state.messages.append({"role": "user", "content": query})
        st.session_state.messages.append({
            "role": "blocked",
            "content": scan_result.warning_message,
            "category_label": cat_label,
        })
        st.session_state.stats["blocked"] += 1
        cats = st.session_state.stats["categories"]
        cats[cat_label] = cats.get(cat_label, 0) + 1

    else:
        # Safe — proceed through RAG → LLM
        st.session_state.messages.append({"role": "user", "content": query})

        with st.spinner("Looking up the answer..."):
            # Step 2: Retrieve context
            context = retrieve_context(query)

            # Step 3: Ask LLM
            if ollama_ok:
                answer = ask_ollama(query, context)
            else:
                answer = (
                    "Ollama is not running. Please start it with `ollama serve` "
                    "and make sure you have pulled a model (e.g. `ollama pull llama3`)."
                )

        st.session_state.messages.append({"role": "assistant", "content": answer})
        st.session_state.stats["answered"] += 1

    st.rerun()


# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.markdown("""
<div style="text-align:center; color:#94a3b8; font-size:0.78rem; margin-top:2rem;">
    Powered by Ollama · LangChain · Streamlit &nbsp;·&nbsp; Sensitive data is never sent to external servers
</div>
""", unsafe_allow_html=True)