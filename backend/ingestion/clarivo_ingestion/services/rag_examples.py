from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer

from clarivo_ingestion.core.logging import get_logger
from clarivo_ingestion.utils.text_extraction import extract_text_from_bytes

logger = get_logger(__name__)


class RAGExampleRetriever:
    """Retrieves similar example documents from Input/Output folders for few-shot learning."""

    def __init__(self, input_dir: Path, output_dir: Path, top_k: int = 3) -> None:
        """
        Initialize the RAG retriever.

        Args:
            input_dir: Path to Input folder containing example documents
            output_dir: Path to Output folder containing corresponding JSON outputs
            top_k: Number of similar examples to retrieve (default: 3)
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.top_k = top_k
        self.embeddings_cache: dict[str, np.ndarray] = {}
        self.texts_cache: dict[str, str] = {}
        self.outputs_cache: dict[str, dict[str, Any]] = {}
        self.model: SentenceTransformer | None = None
        self._initialized = False

    def _initialize_model(self) -> None:
        """Lazy initialization of the embedding model."""
        if self.model is None:
            logger.info("Loading sentence transformer model for RAG embeddings...")
            # Using a lightweight, fast model suitable for document similarity
            self.model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("Sentence transformer model loaded successfully.")

    def _load_all_examples(self) -> None:
        """Load all Input documents and their corresponding Output JSON files."""
        if self._initialized:
            return

        logger.info("Loading example documents from %s", self.input_dir)
        input_files = list(self.input_dir.glob("*"))
        input_files = [f for f in input_files if f.is_file() and f.suffix.lower() in {".pdf", ".docx", ".txt", ".md"}]

        if not input_files:
            logger.warning("No example documents found in %s", self.input_dir)
            return

        self._initialize_model()

        for input_file in input_files:
            base_name = input_file.stem
            output_file = self.output_dir / f"{base_name}.json"

            if not output_file.exists():
                logger.warning("No corresponding output file found for %s (expected %s)", input_file.name, output_file.name)
                continue

            try:
                # Load input document text
                with open(input_file, "rb") as f:
                    content = f.read()
                text = extract_text_from_bytes(input_file.name, content)
                if not text.strip():
                    logger.warning("Empty text extracted from %s", input_file.name)
                    continue

                self.texts_cache[base_name] = text

                # Create embedding
                embedding = self.model.encode(text, normalize_embeddings=True)
                self.embeddings_cache[base_name] = embedding

                # Load output JSON
                with open(output_file, "r", encoding="utf-8") as f:
                    output_data = json.load(f)
                self.outputs_cache[base_name] = output_data

                logger.debug("Loaded example: %s (text length: %d chars)", base_name, len(text))

            except Exception as exc:
                logger.error("Failed to load example %s: %s", input_file.name, exc, exc_info=True)

        self._initialized = True
        logger.info("Loaded %d example document pairs", len(self.embeddings_cache))

    def find_similar_examples(self, query_text: str) -> list[dict[str, Any]]:
        """
        Find the top-k most similar example documents to the query text.

        Args:
            query_text: The text content to find similar examples for

        Returns:
            List of dictionaries containing:
            - 'input_text': The example input document text (truncated)
            - 'output_json': The corresponding structured output JSON
            - 'similarity': Cosine similarity score
            - 'name': Base name of the example file
        """
        self._load_all_examples()

        if not self.embeddings_cache:
            logger.warning("No example documents available for RAG retrieval")
            return []

        if not query_text.strip():
            logger.warning("Empty query text provided for similarity search")
            return []

        self._initialize_model()

        # Create embedding for query
        query_embedding = self.model.encode(query_text, normalize_embeddings=True)

        # Calculate cosine similarities
        similarities = []
        for name, example_embedding in self.embeddings_cache.items():
            similarity = float(np.dot(query_embedding, example_embedding))
            similarities.append((name, similarity))

        # Sort by similarity (descending) and take top-k
        similarities.sort(key=lambda x: x[1], reverse=True)
        top_examples = similarities[: self.top_k]

        results = []
        for name, similarity in top_examples:
            input_text = self.texts_cache.get(name, "")
            output_json = self.outputs_cache.get(name, {})

            # Truncate input text to avoid token limits (keep first 2000 chars)
            truncated_text = input_text[:2000] + "..." if len(input_text) > 2000 else input_text

            results.append(
                {
                    "name": name,
                    "input_text": truncated_text,
                    "output_json": output_json,
                    "similarity": similarity,
                }
            )

            logger.debug("Retrieved example '%s' with similarity %.3f", name, similarity)

        logger.info("Retrieved %d similar examples for RAG", len(results))
        return results

    def format_examples_for_prompt(self, examples: list[dict[str, Any]]) -> str:
        """
        Format examples as few-shot learning context for the LLM prompt.

        Args:
            examples: List of example dictionaries from find_similar_examples()

        Returns:
            Formatted string to include in the prompt
        """
        if not examples:
            return ""

        formatted_parts = [
            "=== FEW-SHOT EXAMPLES ===",
            "Below are examples of similar requirement documents and their structured outputs.",
            "Study these examples carefully to understand:",
            "1. How to extract information accurately from the document",
            "2. How to organize modules and features logically",
            "3. The level of detail expected in summaries and acceptance criteria",
            "4. How to identify personas, requirements, and other elements",
            "",
        ]

        for idx, example in enumerate(examples, 1):
            formatted_parts.append(f"--- Example {idx} (similarity: {example['similarity']:.1%}) ---")
            formatted_parts.append("Input document (excerpt):")
            formatted_parts.append(example["input_text"])
            formatted_parts.append("")
            formatted_parts.append("Expected structured output format:")
            formatted_parts.append(json.dumps(example["output_json"], indent=2))
            formatted_parts.append("")
            formatted_parts.append("")

        formatted_parts.append(
            "=== END EXAMPLES ==="
        )
        formatted_parts.append("")
        formatted_parts.append(
            "IMPORTANT: Follow the structure and level of detail shown in these examples. "
            "Extract information accurately from the document - do not paraphrase unnecessarily. "
            "Group features into logical modules. Provide detailed summaries and acceptance criteria."
        )
        formatted_parts.append("")

        return "\n".join(formatted_parts)

