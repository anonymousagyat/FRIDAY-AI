"""
Vector RAG Oracle — Local Semantic Vector Memory Engine.
Indexes codebases, documents, and notes into an embedded vector store.
Enables sub-second semantic retrieval using cosine similarity and Gemini embeddings.
"""

import os
import json
import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import numpy as np

try:
    from google import genai
except ImportError:
    genai = None

logger = logging.getLogger(__name__)


class VectorMemory:
    """Embedded Vector Database & Semantic Knowledge Retrieval."""

    DEFAULT_EXTENSIONS = {'.py', '.txt', '.md', '.json', '.html', '.css', '.js', '.csv', '.ini', '.yaml', '.yml'}
    EMBEDDING_MODEL = "models/gemini-embedding-001"

    def __init__(self, db_path: Optional[str] = None, gemini_api_key: Optional[str] = None):
        if not db_path:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cache_dir = os.path.join(base_dir, '.cache', 'vector_store')
            os.makedirs(cache_dir, exist_ok=True)
            db_path = os.path.join(cache_dir, 'knowledge.db')

        self.db_path = db_path
        self.api_key = gemini_api_key or ""
        self.client = None

        if self.api_key and genai:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"[VectorMemory] Failed to init genai client: {e}")

        self._init_db()

    def _init_db(self):
        """Create sqlite tables for document chunks and vector embeddings."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding BLOB,
                    indexed_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_file_path ON knowledge_chunks(file_path)")

    def _get_embedding(self, text: str) -> Optional[np.ndarray]:
        """Generate normalized float32 embedding vector for text."""
        if not self.client or not text.strip():
            return None

        try:
            res = self.client.models.embed_content(
                model=self.EMBEDDING_MODEL,
                contents=text[:4000]  # Safe token boundary
            )
            if res and res.embeddings and len(res.embeddings) > 0:
                vec = np.array(res.embeddings[0].values, dtype=np.float32)
                norm = np.linalg.norm(vec)
                if norm > 0:
                    vec = vec / norm
                return vec
        except Exception as e:
            logger.error(f"[VectorMemory] Embedding error: {e}")
        return None

    def chunk_text(self, text: str, chunk_size: int = 800, overlap: int = 150) -> List[str]:
        """Split document text into overlapping semantic windows."""
        if not text:
            return []
        chunks = []
        start = 0
        text_len = len(text)
        while start < text_len:
            end = min(start + chunk_size, text_len)
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start += chunk_size - overlap
            if start >= text_len or end >= text_len:
                break
        return chunks

    def index_file(self, file_path: str) -> int:
        """Index a single document or source code file."""
        if not os.path.exists(file_path):
            return 0

        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.DEFAULT_EXTENSIONS:
            return 0

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception:
            return 0

        chunks = self.chunk_text(content)
        if not chunks:
            return 0

        file_name = os.path.basename(file_path)
        now = datetime.now().isoformat()

        # Remove old chunks for this file
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM knowledge_chunks WHERE file_path = ?", (file_path,))

        inserted = 0
        with sqlite3.connect(self.db_path) as conn:
            for idx, ch in enumerate(chunks):
                vec = self._get_embedding(ch)
                blob = vec.tobytes() if vec is not None else None
                conn.execute("""
                    INSERT INTO knowledge_chunks (file_path, file_name, chunk_index, content, embedding, indexed_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (file_path, file_name, idx, ch, blob, now))
                inserted += 1

        return inserted

    def index_directory(self, dir_path: str, max_files: int = 100) -> Dict[str, Any]:
        """Recursively index a codebase or folder."""
        if not os.path.exists(dir_path):
            return {'success': False, 'message': f"Folder nahi mila: {dir_path}"}

        indexed_files = 0
        total_chunks = 0

        for root, dirs, files in os.walk(dir_path):
            # Skip noise folders
            dirs[:] = [d for d in dirs if d not in ('.git', 'node_modules', '__pycache__', '.cache', 'venv', 'dist', 'build')]
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in self.DEFAULT_EXTENSIONS:
                    fp = os.path.join(root, f)
                    chunks_added = self.index_file(fp)
                    if chunks_added > 0:
                        indexed_files += 1
                        total_chunks += chunks_added
                    if indexed_files >= max_files:
                        break
            if indexed_files >= max_files:
                break

        folder_name = os.path.basename(os.path.normpath(dir_path))
        msg = f"Boss, '{folder_name}' folder me {indexed_files} files aur {total_chunks} chunks index kar liye hain!"
        return {
            'success': True,
            'files_indexed': indexed_files,
            'chunks_indexed': total_chunks,
            'message': msg
        }

    def query(self, question: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """Semantic vector retrieval for a question."""
        q_vec = self._get_embedding(question)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, file_path, file_name, chunk_index, content, embedding FROM knowledge_chunks")
            rows = cursor.fetchall()

        if not rows:
            return []

        results = []
        for r in rows:
            blob = r[5]
            score = 0.0
            if q_vec is not None and blob is not None:
                doc_vec = np.frombuffer(blob, dtype=np.float32)
                # Cosine similarity (both are unit normalized)
                score = float(np.dot(q_vec, doc_vec))
            else:
                # Basic keyword fallback match
                words = set(question.lower().split())
                content_words = set(r[4].lower().split())
                overlap = len(words.intersection(content_words))
                score = overlap / max(1, len(words))

            results.append({
                'id': r[0],
                'file_path': r[1],
                'file_name': r[2],
                'chunk_index': r[3],
                'content': r[4],
                'score': score
            })

        # Sort by similarity score descending
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_k]

    def get_stats(self) -> Dict[str, Any]:
        """Get summary of indexed memory database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT count(*), count(distinct file_path) FROM knowledge_chunks")
            chunk_count, file_count = cursor.fetchone()
        return {
            'files': file_count,
            'chunks': chunk_count,
            'db_path': self.db_path
        }
