import sys
import os
import logging

# Append turboquant to path so we can import its modules when fine-tuning
TURBOQUANT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'turboquant'))
if TURBOQUANT_PATH not in sys.path:
    sys.path.append(TURBOQUANT_PATH)

from core_engine.neural_compressor import NeuralCompressor

logger = logging.getLogger(__name__)

class MemoryManager:
    """
    Handles Caching, Short-Term, and Long-Term Memory loops.
    Integrates Turboquant logic to rapidly compress and retrieve context.
    """
    def __init__(self, vault_path: str = "Vault"):
        self.vault_path = vault_path
        self.short_term_cache = []
        self._compressor = NeuralCompressor(vault_path)

    def store_context(self, context_str: str):
        """Stores dense reasoning paths to avoid I/O bottlenecks."""
        self.short_term_cache.append(context_str)

    def retrieve_context(self) -> str:
        """Rapidly unpacks the current session stream."""
        return "\n".join(self.short_term_cache)

    def compress_to_cluster(self, seed_notes: list, cycles: int = 6, prune_threshold: float = 0.08) -> list:
        """
        Hebbian compression pass over the vault for a given set of seed notes.
        Returns the minimal cluster of neurons that fully reconstructs the seed thought.

        This replaces the Turboquant KV-cache placeholder — the NeuralCompressor
        IS the local compression pass, running entirely offline with pure vector math.
        """
        logger.info(f"[MemoryManager] Running Hebbian compression for seeds: {seed_notes}")
        cluster = self._compressor.run_compression(
            seed_notes=seed_notes,
            cycles=cycles,
            prune_threshold=prune_threshold,
        )
        logger.info(f"[MemoryManager] Cluster → {cluster}")
        return cluster
