
import os
from typing import List

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document


POLICY_FILE = os.path.join(os.path.dirname(__file__), "data", "company_policy.txt")
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # Small, free, runs locally

_vectorstore = None  # Module-level cache so we only build the index once


def _load_and_split() -> List[Document]:
    """Load the policy text file and split into overlapping chunks."""
    loader = TextLoader(POLICY_FILE, encoding="utf-8")
    documents = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,       # Characters per chunk — small enough to stay focused
        chunk_overlap=80,     # Overlap keeps context across chunk boundaries
        separators=["\n\n", "\n", ". ", " "],
    )
    chunks = splitter.split_documents(documents)
    return chunks


def build_vectorstore() -> FAISS:
    """
    Build a FAISS vector store from the policy document.
    This runs once on startup and is cached in memory.
    """
    global _vectorstore

    if _vectorstore is not None:
        return _vectorstore

    chunks = _load_and_split()

    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    _vectorstore = FAISS.from_documents(chunks, embeddings)
    return _vectorstore


def retrieve_context(query: str, k: int = 4) -> str:
    """
    Given a user query, retrieve the top-k most relevant chunks
    from the vector store and return them as a single context string.
    """
    vs = build_vectorstore()
    docs = vs.similarity_search(query, k=k)

    if not docs:
        return "No relevant information found in the company policy."

    context_parts = []
    for i, doc in enumerate(docs, 1):
        context_parts.append(f"[Excerpt {i}]\n{doc.page_content.strip()}")

    return "\n\n".join(context_parts)