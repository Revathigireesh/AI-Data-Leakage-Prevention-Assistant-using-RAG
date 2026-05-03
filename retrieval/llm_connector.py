"""
llm_connector.py
----------------
Connects to a locally running Ollama instance and sends
a prompt (with retrieved context) to the LLM.
Returns a plain-text response string.
"""

import requests
import json


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3"  # Change to "mistral" or "phi3" if preferred

SYSTEM_PROMPT = """You are a helpful HR assistant for a company. 
Your job is to answer employee questions about company policies clearly and concisely.
Only answer based on the provided context. 
If the answer is not in the context, say: "I don't have information on that. Please contact HR directly at hr@company.com"
Keep answers short and friendly. Do not make up information."""


def ask_ollama(user_query: str, context: str) -> str:
    """
    Send a query and retrieved context to Ollama and return the response text.
    """
    prompt = f"""{SYSTEM_PROMPT}

---
COMPANY POLICY CONTEXT:
{context}
---

EMPLOYEE QUESTION: {user_query}

ANSWER:"""

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,      # Low temperature = more factual, less creative
            "num_predict": 300,      # Max tokens in response
        }
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "Sorry, I could not generate a response.").strip()

    except requests.exceptions.ConnectionError:
        return (
            "Could not connect to Ollama. "
            "Please make sure Ollama is running: open a terminal and run `ollama serve`."
        )
    except requests.exceptions.Timeout:
        return "The request timed out. Ollama may be loading the model — please try again in a moment."
    except Exception as e:
        return f"An error occurred while contacting the LLM: {str(e)}"


def check_ollama_running() -> bool:
    """Quick health check — returns True if Ollama is reachable."""
    try:
        r = requests.get("http://localhost:11434", timeout=3)
        return r.status_code == 200
    except Exception:
        return False