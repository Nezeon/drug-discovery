"""
rag/chroma_store.py — ChromaDB vector store for literature RAG.

Manages per-job ChromaDB collections for storing and querying
biomedical abstracts, target evidence, and compound context.

ChromaDB 0.5.x API (breaking changes from 0.4.x):
  - Client: chromadb.PersistentClient(path=...) — not chromadb.Client()
  - Collection.add() takes documents, metadatas, ids — all lists
  - Collection.query() returns dict with "documents", "distances", "metadatas"
  - No .persist() needed — PersistentClient auto-persists
  - Default embedding: all-MiniLM-L6-v2 via sentence-transformers
"""

from __future__ import annotations

import logging
from typing import Any

import chromadb

import config

logger = logging.getLogger(__name__)

# Singleton client — reused across all store instances
_client: chromadb.ClientAPI | None = None


def _get_client() -> chromadb.ClientAPI:
    """Get or create the singleton PersistentClient."""
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=config.CHROMA_PERSIST_DIR)
        logger.info("ChromaDB PersistentClient created at %s", config.CHROMA_PERSIST_DIR)
    return _client


class LiteratureStore:
    """
    ChromaDB-backed store for biomedical literature abstracts.

    Each job gets its own collection named {job_id}_literature.
    Uses ChromaDB's default embedding function (all-MiniLM-L6-v2).
    """

    def store_abstracts(self, job_id: str, abstracts: list[dict[str, Any]]) -> int:
        """
        Embed and store abstracts in ChromaDB.

        Args:
            job_id: The pipeline job identifier.
            abstracts: List of {pmid, title, abstract, pub_date, authors}.

        Returns:
            Number of abstracts stored.
        """
        if not abstracts:
            return 0

        client = _get_client()
        collection_name = f"{job_id}_literature"
        collection = client.get_or_create_collection(name=collection_name)

        documents = []
        metadatas = []
        ids = []

        for i, abstract in enumerate(abstracts):
            text = abstract.get("abstract") or ""
            title = abstract.get("title") or ""
            if not text:
                continue

            # Combine title + abstract for better retrieval
            doc_text = f"{title}\n\n{text}" if title else text

            pmid = abstract.get("pmid") or f"doc_{i}"
            documents.append(doc_text)
            metadatas.append({
                "pmid": str(pmid),
                "title": title,
                "pub_date": abstract.get("pub_date") or "",
                "authors": abstract.get("authors") or "",
                "source": "pubmed" if abstract.get("pmid") else "europepmc",
            })
            ids.append(f"{job_id}_{pmid}_{i}")

        if not documents:
            return 0

        # ChromaDB 0.5.x: add in batches to avoid memory issues
        batch_size = 100
        stored = 0
        for start in range(0, len(documents), batch_size):
            end = start + batch_size
            try:
                collection.add(
                    documents=documents[start:end],
                    metadatas=metadatas[start:end],
                    ids=ids[start:end],
                )
                stored += len(documents[start:end])
            except Exception as exc:
                logger.error("ChromaDB add failed (batch %d-%d): %s", start, end, exc)

        logger.info("Stored %d abstracts in collection '%s'", stored, collection_name)
        return stored

    def query_relevant(
        self,
        job_id: str,
        query: str,
        n_results: int = 5,
    ) -> list[str]:
        """
        Query ChromaDB for the most relevant abstract chunks.

        Args:
            job_id: The pipeline job identifier.
            query: Natural language query string.
            n_results: Number of results to return.

        Returns:
            List of relevant document strings (title + abstract).
        """
        client = _get_client()
        collection_name = f"{job_id}_literature"

        try:
            collection = client.get_collection(name=collection_name)
        except Exception:
            logger.warning("Collection '%s' not found", collection_name)
            return []

        try:
            results = collection.query(
                query_texts=[query],
                n_results=n_results,
            )
            # results["documents"] is a list of lists (one per query)
            docs = results.get("documents", [[]])[0]
            return docs
        except Exception as exc:
            logger.error("ChromaDB query failed: %s", exc)
            return []

    def get_abstracts_with_metadata(
        self,
        job_id: str,
        query: str,
        n_results: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Query and return abstracts with their metadata (pmid, title, etc.).
        """
        client = _get_client()
        collection_name = f"{job_id}_literature"

        try:
            collection = client.get_collection(name=collection_name)
        except Exception:
            return []

        try:
            results = collection.query(
                query_texts=[query],
                n_results=n_results,
                include=["documents", "metadatas"],
            )
            docs = results.get("documents", [[]])[0]
            metas = results.get("metadatas", [[]])[0]
            return [
                {"text": doc, **meta}
                for doc, meta in zip(docs, metas)
            ]
        except Exception as exc:
            logger.error("ChromaDB query with metadata failed: %s", exc)
            return []

    @staticmethod
    def delete_job_collections(job_id: str) -> None:
        """Delete all collections for a given job ID."""
        client = _get_client()
        suffixes = ["_literature", "_target_evidence", "_compound_context"]
        for suffix in suffixes:
            name = f"{job_id}{suffix}"
            try:
                client.delete_collection(name=name)
                logger.info("Deleted collection '%s'", name)
            except Exception:
                pass  # Collection may not exist — that's fine
