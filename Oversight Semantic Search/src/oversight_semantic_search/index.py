from __future__ import annotations

import json
import math
import re
import sqlite3
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from oversight_semantic_search.config import SearchConfig

TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9\-_/]+")
DEFAULT_STOPWORDS = {
    "a", "about", "after", "all", "also", "an", "and", "are", "as", "at", "be", "been",
    "being", "between", "by", "can", "for", "from", "has", "have", "in", "into", "is",
    "it", "its", "of", "on", "or", "that", "the", "their", "this", "to", "was", "were",
    "will", "with", "within", "without",
}


@dataclass(slots=True)
class ReportDocument:
    canonical_id: str
    title: str
    summary: str
    publication_date: str | None
    agency: str | None
    subagency: str | None
    report_type: str | None
    source_url: str
    detail_url: str
    download_url: str | None
    text: str


class SemanticSearchIndex:
    def __init__(self, config: SearchConfig | None = None) -> None:
        self.config = config or SearchConfig.from_env()
        self._loaded = False
        self._documents: list[dict[str, Any]] = []
        self._vocabulary: dict[str, int] = {}
        self._idf: np.ndarray | None = None
        self._projection: np.ndarray | None = None
        self._document_vectors: np.ndarray | None = None
        self._stopwords = set(DEFAULT_STOPWORDS)
        if self.config.stopword_path and self.config.stopword_path.exists():
            self._stopwords |= {
                line.strip().lower()
                for line in self.config.stopword_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            }

    @property
    def metadata_path(self) -> Path:
        return self.config.index_dir / "metadata.json"

    @property
    def matrix_path(self) -> Path:
        return self.config.index_dir / "vectors.npz"

    def ensure_ready(self, rebuild: bool = False) -> None:
        if rebuild or not (self.metadata_path.exists() and self.matrix_path.exists()):
            self.build()
        elif not self._loaded:
            try:
                self.load()
            except Exception:
                self.build()

    def build(self) -> None:
        documents = self._load_documents()
        if not documents:
            raise RuntimeError(f"No reports found in {self.config.oig_db_path}")

        tokenized = [self._tokenize(doc.text) for doc in documents]
        vocab, idf = self._build_vocabulary(tokenized)
        tfidf_matrix = self._build_tfidf_matrix(tokenized, vocab, idf)
        doc_vectors, projection = self._build_latent_space(tfidf_matrix)

        self.config.index_dir.mkdir(parents=True, exist_ok=True)
        metadata_tmp_path = self.metadata_path.with_name(f"{self.metadata_path.stem}.tmp{self.metadata_path.suffix}")
        matrix_tmp_path = self.matrix_path.with_name(f"{self.matrix_path.stem}.tmp{self.matrix_path.suffix}")

        with metadata_tmp_path.open("w", encoding="utf-8") as handle:
            json.dump(
                {
                    "config": {
                        "chunk_char_limit": self.config.chunk_char_limit,
                        "max_features": self.config.max_features,
                        "latent_dimensions": self.config.latent_dimensions,
                        "min_token_length": self.config.min_token_length,
                        "oig_db_path": str(self.config.oig_db_path),
                    },
                    "documents": [asdict(doc) for doc in documents],
                    "vocabulary": vocab,
                    "idf": idf.tolist(),
                },
                handle,
                ensure_ascii=True,
                indent=2,
            )
        np.savez_compressed(
            matrix_tmp_path,
            document_vectors=doc_vectors,
            projection=projection,
        )
        metadata_tmp_path.replace(self.metadata_path)
        matrix_tmp_path.replace(self.matrix_path)

        self._documents = [asdict(doc) for doc in documents]
        self._vocabulary = vocab
        self._idf = idf
        self._projection = projection
        self._document_vectors = doc_vectors
        self._loaded = True

    def load(self) -> None:
        metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        vectors = np.load(self.matrix_path)
        self._documents = metadata["documents"]
        self._vocabulary = {str(k): int(v) for k, v in metadata["vocabulary"].items()}
        self._idf = np.asarray(metadata["idf"], dtype=np.float32)
        self._projection = vectors["projection"].astype(np.float32)
        self._document_vectors = vectors["document_vectors"].astype(np.float32)
        self._loaded = True

    def search(self, query_text: str, top_k: int = 10) -> list[dict[str, Any]]:
        self.ensure_ready()
        if not query_text or not query_text.strip():
            return []

        assert self._idf is not None
        assert self._projection is not None
        assert self._document_vectors is not None

        query_vector = self._encode_query(query_text)
        if not np.any(query_vector):
            return []

        scores = self._document_vectors @ query_vector
        best_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for index in best_indices:
            if scores[index] <= 0:
                continue
            item = dict(self._documents[int(index)])
            item["score"] = float(scores[index])
            results.append(item)
        return results

    def search_project(self, title: str, objective: str, top_k: int = 10) -> list[dict[str, Any]]:
        query = "\n".join(part.strip() for part in [title, objective] if part and part.strip())
        return self.search(query, top_k=top_k)

    def _load_documents(self) -> list[ReportDocument]:
        connection = sqlite3.connect(self.config.oig_db_path)
        connection.row_factory = sqlite3.Row
        try:
            reports = connection.execute(
                """
                SELECT
                    canonical_id,
                    title,
                    COALESCE(summary, '') AS summary,
                    publication_date,
                    agency,
                    subagency,
                    report_type,
                    source_url,
                    detail_url,
                    download_url
                FROM reports
                ORDER BY canonical_id
                """
            ).fetchall()

            chunk_rows = connection.execute(
                """
                SELECT canonical_id, text
                FROM report_chunks
                ORDER BY canonical_id, chunk_index
                """
            )

            chunks_by_report: dict[str, list[str]] = {}
            char_counts: dict[str, int] = {}
            for row in chunk_rows:
                canonical_id = row["canonical_id"]
                chunk_text = (row["text"] or "").strip()
                if not chunk_text:
                    continue
                chunks_by_report.setdefault(canonical_id, [])
                char_counts.setdefault(canonical_id, 0)
                remaining = self.config.chunk_char_limit - char_counts[canonical_id]
                if remaining <= 0:
                    continue
                trimmed = chunk_text[:remaining]
                chunks_by_report[canonical_id].append(trimmed)
                char_counts[canonical_id] += len(trimmed)

            documents = []
            for row in reports:
                chunk_text = "\n".join(chunks_by_report.get(row["canonical_id"], []))
                combined_text = "\n\n".join(
                    part
                    for part in [
                        row["title"],
                        row["summary"],
                        row["agency"] or "",
                        row["subagency"] or "",
                        row["report_type"] or "",
                        chunk_text,
                    ]
                    if part and part.strip()
                )
                documents.append(
                    ReportDocument(
                        canonical_id=row["canonical_id"],
                        title=row["title"],
                        summary=row["summary"],
                        publication_date=row["publication_date"],
                        agency=row["agency"],
                        subagency=row["subagency"],
                        report_type=row["report_type"],
                        source_url=row["source_url"],
                        detail_url=row["detail_url"],
                        download_url=row["download_url"],
                        text=combined_text,
                    )
                )
            return documents
        finally:
            connection.close()

    def _tokenize(self, text: str) -> list[str]:
        tokens = []
        for raw_token in TOKEN_RE.findall(text.lower()):
            if len(raw_token) < self.config.min_token_length:
                continue
            if raw_token in self._stopwords:
                continue
            tokens.append(raw_token)
        return tokens

    def _build_vocabulary(self, tokenized_documents: list[list[str]]) -> tuple[dict[str, int], np.ndarray]:
        document_frequencies: Counter[str] = Counter()
        for tokens in tokenized_documents:
            document_frequencies.update(set(tokens))

        ranked_terms = [
            term
            for term, doc_freq in document_frequencies.most_common()
            if doc_freq >= 2
        ][: self.config.max_features]
        vocabulary = {term: idx for idx, term in enumerate(ranked_terms)}
        total_documents = max(len(tokenized_documents), 1)
        idf = np.zeros(len(vocabulary), dtype=np.float32)
        for term, idx in vocabulary.items():
            doc_freq = document_frequencies[term]
            idf[idx] = math.log((1 + total_documents) / (1 + doc_freq)) + 1.0
        return vocabulary, idf

    def _build_tfidf_matrix(
        self,
        tokenized_documents: list[list[str]],
        vocabulary: dict[str, int],
        idf: np.ndarray,
    ) -> np.ndarray:
        matrix = np.zeros((len(tokenized_documents), len(vocabulary)), dtype=np.float32)
        for row_index, tokens in enumerate(tokenized_documents):
            counts = Counter(token for token in tokens if token in vocabulary)
            if not counts:
                continue
            max_count = max(counts.values())
            for token, count in counts.items():
                column_index = vocabulary[token]
                matrix[row_index, column_index] = (0.5 + 0.5 * (count / max_count)) * idf[column_index]

        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return matrix / norms

    def _build_latent_space(self, tfidf_matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        gram_matrix = tfidf_matrix @ tfidf_matrix.T
        eigenvalues, eigenvectors = np.linalg.eigh(gram_matrix)
        order = np.argsort(eigenvalues)[::-1]
        eigenvalues = np.clip(eigenvalues[order], a_min=0.0, a_max=None)
        eigenvectors = eigenvectors[:, order]

        non_zero = eigenvalues > 1e-8
        eigenvalues = eigenvalues[non_zero]
        eigenvectors = eigenvectors[:, non_zero]
        if eigenvalues.size == 0:
            raise RuntimeError("The semantic index could not derive any latent dimensions.")

        dimensions = min(self.config.latent_dimensions, eigenvalues.size)
        singular_values = np.sqrt(eigenvalues[:dimensions]).astype(np.float32)
        left_vectors = eigenvectors[:, :dimensions].astype(np.float32)
        projection = (tfidf_matrix.T @ left_vectors) / singular_values[np.newaxis, :]
        projection = projection.astype(np.float32)

        document_vectors = left_vectors * singular_values[np.newaxis, :]
        document_vectors = self._normalize_rows(document_vectors)
        projection = self._normalize_rows(projection.T).T
        return document_vectors.astype(np.float32), projection.astype(np.float32)

    def _encode_query(self, query_text: str) -> np.ndarray:
        assert self._idf is not None
        assert self._projection is not None

        query_terms = self._tokenize(query_text)
        if not query_terms:
            return np.zeros(self._projection.shape[1], dtype=np.float32)

        counts = Counter(term for term in query_terms if term in self._vocabulary)
        if not counts:
            return np.zeros(self._projection.shape[1], dtype=np.float32)

        tfidf = np.zeros(len(self._vocabulary), dtype=np.float32)
        max_count = max(counts.values())
        for term, count in counts.items():
            index = self._vocabulary[term]
            tfidf[index] = (0.5 + 0.5 * (count / max_count)) * self._idf[index]

        norm = np.linalg.norm(tfidf)
        if norm > 0:
            tfidf /= norm

        query_vector = tfidf @ self._projection
        query_norm = np.linalg.norm(query_vector)
        if query_norm > 0:
            query_vector /= query_norm
        return query_vector.astype(np.float32)

    @staticmethod
    def _normalize_rows(matrix: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return matrix / norms
