"""
J.A.R.V.I.S. Vector Memory Module
==================================
Semantic long-term memory using embeddings + cosine similarity.
Replaces the flat memory.txt approach with intelligent recall.

Primary: Gemini embedding API via OpenAI-compatible client
Storage: JSON file with embedded vectors + numpy cosine similarity
Fallback: Raw memory.txt if embeddings fail
"""

import os
import json
import time
import re
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
MEMORY_DB_PATH = os.path.join(PROJECT_ROOT, "data", "memory_db.json")
MEMORY_TXT_PATH = os.path.join(PROJECT_ROOT, "data", "memory.txt")
EMBEDDING_MODEL = "gemini-embedding-001"


class VectorMemory:
    """Lightweight vector memory store using Gemini embeddings + numpy cosine similarity."""

    def __init__(self, api_key=None, base_url=None):
        self.memories = []  # List of {"text": str, "embedding": list[float], "timestamp": str}
        self._ready = False
        self._genai_client = None

        if api_key:
            try:
                from google import genai
                self._genai_client = genai.Client(api_key=api_key)
                self._ready = True
            except Exception:
                self._ready = False

        self._load()

    def _load(self):
        """Load memories from the JSON database file."""
        if os.path.exists(MEMORY_DB_PATH):
            try:
                with open(MEMORY_DB_PATH, "r", encoding="utf-8") as f:
                    self.memories = json.load(f)
            except (json.JSONDecodeError, Exception):
                self.memories = []

    def _save(self):
        """Persist memories to the JSON database file."""
        try:
            with open(MEMORY_DB_PATH, "w", encoding="utf-8") as f:
                json.dump(self.memories, f, ensure_ascii=False)
        except Exception as e:
            print(f"[!] Vector Memory save error: {e}")

    def _embed(self, text):
        """Generate an embedding vector for the given text using Gemini native SDK."""
        if not self._ready or not self._genai_client:
            return None
            
        import time
        if hasattr(self, '_disable_until') and time.time() < self._disable_until:
            return None
            
        from google import genai
        import os
        
        # Determine the current key and all backups
        current_key = None
        try:
            current_key = self._genai_client._config.api_key
        except AttributeError:
            current_key = os.getenv("AI_API_KEY")
            
        keys_to_try = [current_key] if current_key else []
        gem_key = os.getenv("GEMINI_API_KEY")
        if gem_key and gem_key not in keys_to_try:
            keys_to_try.insert(0, gem_key)
            
        for i in range(1, 11):
            k = os.getenv(f"BACKUP_{i}_API_KEY")
            if not k or k.startswith("PASTE") or k.startswith("YOUR") or k.startswith("nvapi"):
                continue
            if k not in keys_to_try:
                keys_to_try.append(k)

        last_err = None
        for key in keys_to_try:
            try:
                temp_client = genai.Client(api_key=key)
                result = temp_client.models.embed_content(
                    model=EMBEDDING_MODEL,
                    contents=text[:2048]
                )
                self._genai_client = temp_client
                return list(result.embeddings[0].values)
            except Exception as e:
                last_err = e
                continue

        print(f"[!] Embedding error: {last_err}")
        self._disable_until = time.time() + 60
        return None

    def _cosine_similarity(self, vec_a, vec_b):
        """Compute cosine similarity between two vectors."""
        a = np.array(vec_a, dtype=np.float32)
        b = np.array(vec_b, dtype=np.float32)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def is_ready(self):
        """Check if the vector memory system is operational."""
        return self._ready and self._genai_client is not None

    def is_seeded(self):
        """Check if the database has been seeded with initial memories."""
        return len(self.memories) > 0

    def seed_from_file(self, filepath=None):
        """
        One-time import: reads memory.txt, splits into logical chunks,
        embeds each chunk, and stores them. Only runs if DB is empty.
        """
        if self.is_seeded():
            return f"Memory already seeded with {len(self.memories)} entries."

        filepath = filepath or MEMORY_TXT_PATH
        if not os.path.exists(filepath):
            return "No memory file found to seed from."

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                raw = f.read()
        except Exception as e:
            return f"Failed to read memory file: {e}"

        # Split by markdown section headers (# or ## or ### or ---)
        chunks = re.split(r'\n(?=#{1,3}\s|\-{3,})', raw)

        # Further split large chunks (> 500 chars) by double newlines
        final_chunks = []
        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk or len(chunk) < 20:
                continue
            # Remove comment headers
            if chunk.startswith("# ===="):
                continue
            if len(chunk) > 500:
                sub_chunks = chunk.split("\n\n")
                for sc in sub_chunks:
                    sc = sc.strip()
                    if sc and len(sc) > 20:
                        final_chunks.append(sc)
            else:
                final_chunks.append(chunk)

        seeded = 0
        for chunk in final_chunks:
            embedding = self._embed(chunk)
            if embedding is not None:
                self.memories.append({
                    "text": chunk,
                    "embedding": embedding,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
                })
                seeded += 1
            else:
                # Store without embedding as fallback
                self.memories.append({
                    "text": chunk,
                    "embedding": None,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
                })
                seeded += 1

        self._save()
        return f"Seeded {seeded} memory chunks from {filepath}."

    def remember(self, text):
        """Store a new memory with its embedding."""
        if not text or len(text.strip()) < 5:
            return "Memory too short to store."

        text = text.strip()

        # Check for near-duplicates using keyword overlap
        for mem in self.memories:
            if mem["text"].strip().lower() == text.lower():
                return "This memory already exists."

        embedding = self._embed(text)
        self.memories.append({
            "text": text,
            "embedding": embedding,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
        })
        self._save()
        return f"Memory stored successfully: '{text[:60]}...'" if len(text) > 60 else f"Memory stored successfully: '{text}'"

    def recall(self, query, n=5):
        """
        Retrieve the top N most relevant memories for the given query.
        Returns a formatted string for injection into the system prompt.
        """
        if not self.memories:
            return self._fallback_recall()

        query_embedding = self._embed(query)

        if query_embedding is None:
            # Embedding failed — fall back to keyword matching
            return self._keyword_recall(query, n)

        scored = []
        for mem in self.memories:
            if mem.get("embedding") is None:
                continue
            similarity = self._cosine_similarity(query_embedding, mem["embedding"])
            scored.append((similarity, mem["text"]))

        if not scored:
            return self._keyword_recall(query, n)

        scored.sort(reverse=True, key=lambda x: x[0])
        top = scored[:n]

        # Only include memories with reasonable similarity (> 0.3)
        relevant = [text for sim, text in top if sim > 0.3]

        if not relevant:
            return self._keyword_recall(query, n)

        return "\n---\n".join(relevant)

    def _keyword_recall(self, query, n=5):
        """Fallback: simple keyword matching when embeddings fail."""
        query_words = set(query.lower().split())
        scored = []
        for mem in self.memories:
            mem_words = set(mem["text"].lower().split())
            overlap = len(query_words & mem_words)
            if overlap > 0:
                scored.append((overlap, mem["text"]))

        scored.sort(reverse=True, key=lambda x: x[0])
        top = [text for _, text in scored[:n]]
        return "\n---\n".join(top) if top else self._fallback_recall()

    def _fallback_recall(self):
        """Ultimate fallback: read raw memory.txt."""
        try:
            with open(MEMORY_TXT_PATH, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            return ""

    def get_all_memories(self):
        """Return all stored memory texts (for settings UI export)."""
        return [m["text"] for m in self.memories]

    def get_all_formatted(self):
        """Return all memories as a single formatted string."""
        if not self.memories:
            return self._fallback_recall()
        return "\n---\n".join(m["text"] for m in self.memories)

    def delete_memory(self, index):
        """Delete a memory by index."""
        if 0 <= index < len(self.memories):
            removed = self.memories.pop(index)
            self._save()
            return f"Deleted memory: '{removed['text'][:60]}...'"
        return "Invalid memory index."

    def clear_all(self):
        """Clear all memories (dangerous — requires confirmation)."""
        self.memories = []
        self._save()
        return "All memories cleared."

    def stats(self):
        """Return memory statistics."""
        total = len(self.memories)
        with_embeddings = sum(1 for m in self.memories if m.get("embedding") is not None)
        return {
            "total_memories": total,
            "with_embeddings": with_embeddings,
            "without_embeddings": total - with_embeddings,
            "db_file": MEMORY_DB_PATH,
            "db_exists": os.path.exists(MEMORY_DB_PATH)
        }


# Module-level singleton (initialized lazily by jarvis_local.py)
_instance = None


def get_memory(api_key=None, base_url=None):
    """Get or create the global VectorMemory singleton."""
    global _instance
    if _instance is None:
        _instance = VectorMemory(api_key=api_key, base_url=base_url)
    return _instance


def init_and_seed(api_key, base_url):
    """Initialize the vector memory and seed from memory.txt if needed."""
    mem = get_memory(api_key, base_url)
    if mem.is_ready() and not mem.is_seeded():
        result = mem.seed_from_file()
        print(f"[*] Vector Memory: {result}")
    elif mem.is_seeded():
        stats = mem.stats()
        print(f"[*] Vector Memory: {stats['total_memories']} memories loaded ({stats['with_embeddings']} with embeddings)")
    else:
        print("[!] Vector Memory: Embedding API unavailable. Using fallback memory.")
    return mem
