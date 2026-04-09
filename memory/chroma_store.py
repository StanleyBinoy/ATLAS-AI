# This module manages persistent ChromaDB memory storage and retrieval for ATLAS.
from datetime import datetime
import hashlib

import chromadb

import config


class LocalEmbeddingFunction:
    """Create simple deterministic local embeddings without external downloads."""

    def name(self):
        """Return the embedding function name expected by ChromaDB."""
        return "atlas-local-embedding"

    def embed_query(self, input):
        """Embed one query string for ChromaDB query compatibility."""
        if isinstance(input, list):
            input = " ".join(str(item) for item in input)
        return self._embed_text(input)

    def embed_documents(self, input):
        """Embed a list of documents for ChromaDB document compatibility."""
        return [self._embed_text(text) for text in input]

    def __call__(self, input):
        """Convert input texts into fixed-size numeric vectors."""
        return self.embed_documents(input)

    def _embed_text(self, text, dimensions=64):
        """Map a text string into a lightweight deterministic embedding vector."""
        text = str(text)
        vector = [0.0] * dimensions
        words = text.lower().split()

        if not words:
            return vector

        for word in words:
            digest = hashlib.sha256(word.encode("utf-8")).digest()
            index = digest[0] % dimensions
            value = (digest[1] / 255.0) + 0.01
            vector[index] += value

        norm = sum(value * value for value in vector) ** 0.5
        if norm:
            vector = [value / norm for value in vector]

        return vector


def _get_collection():
    """Create or return the ATLAS memory collection if ChromaDB is available."""
    try:
        client = chromadb.PersistentClient(path=config.CHROMA_DB_PATH)
        return client.get_or_create_collection(
            "atlas_memory",
            embedding_function=LocalEmbeddingFunction(),
        )
    except Exception as exc:
        if "Embedding function conflict" in str(exc):
            try:
                client = chromadb.PersistentClient(path=config.CHROMA_DB_PATH)
                client.delete_collection("atlas_memory")
                return client.create_collection(
                    "atlas_memory",
                    embedding_function=LocalEmbeddingFunction(),
                )
            except Exception as recreate_exc:
                print(f"Memory error: {recreate_exc}")
                return None
        print(f"Memory error: {exc}")
        return None


def is_memory_available():
    """Return whether the ChromaDB memory collection can be reached."""
    return _get_collection() is not None


def save_memory(text, metadata=None):
    """Save a memory entry with an optional metadata dictionary."""
    collection = _get_collection()
    if collection is None:
        return

    memory_id = datetime.now().strftime("%Y%m%d%H%M%S%f")

    try:
        collection.add(
            ids=[memory_id],
            documents=[text],
            metadatas=[metadata or {}],
        )
        print("Memory saved successfully.")
    except Exception as exc:
        print(f"Memory save failed: {exc}")


def search_memory(query, n_results=3):
    """Return the most relevant memory documents for a search query."""
    collection = _get_collection()
    if collection is None:
        return []

    try:
        embedding_function = LocalEmbeddingFunction()
        query_embedding = embedding_function._embed_text(query)
        results = collection.query(query_embeddings=[query_embedding], n_results=n_results)
        return results.get("documents", [[]])[0]
    except Exception as exc:
        print(f"Memory search failed: {exc}")
        return []


def clear_memory():
    """Delete all stored memories after asking the user for confirmation."""
    confirmation = input("Are you sure you want to delete all memories? (yes/no): ")
    if confirmation.strip().lower() != "yes":
        print("Memory clear cancelled.")
        return

    collection = _get_collection()
    if collection is None:
        return

    try:
        existing = collection.get()
        ids = existing.get("ids", [])
        if ids:
            collection.delete(ids=ids)
        print("All memories cleared.")
    except Exception as exc:
        print(f"Memory clear failed: {exc}")


def get_positive_examples(n=5):
    """Return the most recent positively rated memory documents."""
    collection = _get_collection()
    if collection is None:
        return []

    try:
        results = collection.get(where={"feedback": "positive"}, limit=n)
        documents = results.get("documents", [])
        flattened = []
        for item in documents:
            if isinstance(item, list):
                flattened.extend(str(text) for text in item if text)
            elif item:
                flattened.append(str(item))
        return flattened
    except Exception as exc:
        print(f"Positive memory lookup failed: {exc}")
        return []
