"""
neural_compressor.py
====================
Living Hebbian Neural Field on the Obsidian Vault.

Every note = one neuron.
Every [[link]] = one synapse with a multi-dimensional vector.
One compression pass = fire → spread via cosine similarity → strengthen
                       co-firing vectors → prune below threshold.

No LLM. No external services. Pure local vector dynamics.

Phase 1:  4D vectors  (logical, semantic, temporal, contextual)
Phase 2:  8D vectors  — call increase_dimensions(8)
          Auto-axioms  — call auto_tag_axioms("axioms")
"""

import json
import math
import logging
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────
_SYSTEM_FILES = {"query.md", "compressed-memory.md", "neurons.json"}
_SYSTEM_STEMS = {"query", "compressed-memory"}


class NeuralCompressor:
    """
    Integrated engine module.  Can be instantiated from any other core_engine
    component (MemoryManager, GraphAnalyzer, SimulationBuilder …).

    Args:
        vault_path  : absolute or relative path to the Obsidian vault folder.
        neurons_file: path to the JSON persistence file (default: vault/neurons.json).
        dim         : synapse vector dimensionality {logical, semantic, temporal, contextual}.
    """

    def __init__(self, vault_path: str, neurons_file: str | None = None, dim: int = 4):
        self.vault = Path(vault_path)
        self.neurons_file = Path(neurons_file) if neurons_file else self.vault / "neurons.json"
        self.dim = dim

    # ─────────────────────────────────────────
    # Math helpers
    # ─────────────────────────────────────────

    def cosine_sim(self, a: list[float], b: list[float]) -> float:
        """Cosine similarity between two equal-length vectors."""
        dot = sum(x * y for x, y in zip(a, b))
        mag_a = math.sqrt(sum(x * x for x in a))
        mag_b = math.sqrt(sum(x * x for x in b))
        return dot / (mag_a * mag_b + 1e-9)

    def _vec_magnitude(self, vec: list[float]) -> float:
        return math.sqrt(sum(x * x for x in vec))

    def _init_vector(self, source: str, target: str) -> list[float]:
        """
        Deterministic pseudo-random initial vector derived from the
        source→target pair (no randomness dependency, reproducible).
        """
        seed = hash(source + target) % 10_000
        return [(seed + i * 137) % 1000 / 1000.0 for i in range(self.dim)]

    # ─────────────────────────────────────────
    # Vault scanning
    # ─────────────────────────────────────────

    def _all_md_files(self):
        return [
            md for md in self.vault.glob("**/*.md")
            if md.name not in _SYSTEM_FILES and md.stem not in _SYSTEM_STEMS
        ]

    def _extract_links(self, text: str) -> list[str]:
        """Parse all [[Target]] wikilinks from note body."""
        targets = []
        for part in text.split("[[")[1:]:
            if "]]" in part:
                raw = part.split("]]")[0].strip()
                # Handle [[Target|Alias]] format
                target = raw.split("|")[0].strip()
                if target:
                    targets.append(target)
        return targets

    # ─────────────────────────────────────────
    # Persistence
    # ─────────────────────────────────────────

    def load_neurons(self) -> dict:
        """
        Load network state from neurons.json.
        On first run, auto-builds from every [[link]] in the vault.
        """
        if self.neurons_file.exists():
            with open(self.neurons_file, encoding="utf-8") as f:
                data = json.load(f)
            # Pad vectors if DIM was upgraded
            for note, nd in data.items():
                for target, vec in nd.get("synapses", {}).items():
                    while len(vec) < self.dim:
                        vec.append(0.5)
            logger.info(f"[NeuralCompressor] Loaded {len(data)} neurons from {self.neurons_file}")
            return data

        logger.info("[NeuralCompressor] First run — building network from vault links …")
        return self._build_from_vault()

    def _build_from_vault(self) -> dict:
        """Scan vault and construct the initial neuron/synapse map."""
        neurons: dict = {}

        # Register all notes as neurons
        for md in self._all_md_files():
            neurons[md.stem] = {
                "activation": 0.0,
                "synapses": {},
                "fixed": False,
            }

        # Parse links → synapses
        for md in self._all_md_files():
            name = md.stem
            try:
                text = md.read_text(encoding="utf-8")
            except Exception:
                continue

            for target in self._extract_links(text):
                if target in neurons and target != name:
                    neurons[name]["synapses"][target] = self._init_vector(name, target)

        logger.info(
            f"[NeuralCompressor] Built {len(neurons)} neurons "
            f"and {sum(len(n['synapses']) for n in neurons.values())} synapses."
        )
        return neurons

    def save_neurons(self, neurons: dict) -> None:
        with open(self.neurons_file, "w", encoding="utf-8") as f:
            json.dump(neurons, f, indent=2)

    # ─────────────────────────────────────────
    # Core Simulation
    # ─────────────────────────────────────────

    def run_compression(
        self,
        seed_notes: list[str],
        cycles: int = 6,
        prune_threshold: float = 0.08,
        activation_threshold: float = 0.12,
        decay: float = 0.75,
    ) -> list[str]:
        """
        Execute a full Hebbian compression pass.

        Steps per cycle:
          1. Propagate activation via cosine similarity (with decay).
          2. Reinforce synapse vectors for co-firing pairs (Hebbian update).
          3. Prune synapses whose magnitude drops below prune_threshold.
          4. (Fixed neurons never prune.)

        Returns:
            Sorted list of note names whose final activation > activation_threshold.
        """
        neurons = self.load_neurons()

        # ── Seed ──────────────────────────────
        seeded = []
        for note in seed_notes:
            if note in neurons:
                neurons[note]["activation"] = 1.0
                seeded.append(note)
            else:
                logger.warning(f"[NeuralCompressor] Seed '{note}' not in network — skipped.")

        logger.info(f"[NeuralCompressor] Seeds fired: {seeded}")

        # ── Hebbian cycles ─────────────────────
        for cycle in range(cycles):
            new_act: dict[str, float] = defaultdict(float)

            for note, data in neurons.items():
                if data["activation"] < 0.01:
                    continue
                for target, vec in data["synapses"].items():
                    if target not in neurons:
                        continue
                    # Cross-synapse similarity: compare source→target vec against
                    # target's own synaptic "signature" (mean of its outgoing vecs)
                    target_vecs = list(neurons[target]["synapses"].values())
                    if target_vecs:
                        ref_vec = [
                            sum(v[i] for v in target_vecs) / len(target_vecs)
                            for i in range(self.dim)
                        ]
                        sim = self.cosine_sim(vec, ref_vec)
                    else:
                        sim = self.cosine_sim(vec, vec)  # self-ref fallback

                    new_act[target] += data["activation"] * sim * decay

            # ── Update activations ─────────────
            for note, data in neurons.items():
                act = new_act.get(note, 0.0)
                data["activation"] = max(0.0, min(act, 1.0))  # clamp [0, 1]

            # ── Hebbian reinforcement + prune ──
            for note, data in neurons.items():
                is_fixed = data.get("fixed", False)
                for target in list(data["synapses"].keys()):
                    vec = data["synapses"][target]
                    target_is_fixed = neurons.get(target, {}).get("fixed", False)

                    # Strengthen if both ends co-fired
                    if new_act.get(note, 0.0) > 0.15 and new_act.get(target, 0.0) > 0.15:
                        for i in range(self.dim):
                            vec[i] = vec[i] * 0.92 + 0.08  # Hebbian pull

                    # Prune weak links (skip fixed neurons)
                    mag = self._vec_magnitude(vec)
                    if mag < prune_threshold and not is_fixed and not target_is_fixed:
                        del data["synapses"][target]

            logger.debug(
                f"  Cycle {cycle + 1}/{cycles} — "
                f"active: {sum(1 for d in neurons.values() if d['activation'] > 0.01)}"
            )

        # ── Collect compressed cluster ─────────
        cluster = sorted(
            n for n, d in neurons.items() if d["activation"] > activation_threshold
        )

        self.save_neurons(neurons)
        logger.info(f"[NeuralCompressor] Compression complete → {len(cluster)} neurons in cluster.")
        return cluster

    def integrate_new_note(self, note_name: str) -> bool:
        """
        Dynamically adds a new note to the neural field.
        Scans for links and initializes synapses.
        """
        neurons = self.load_neurons()
        if note_name in neurons:
            return False
            
        md_file = self.vault / f"{note_name}.md"
        if not md_file.exists():
            return False
            
        is_fixed = any(x in note_name.lower() for x in ["guidance", "policy", "axiom"])
        
        if note_name not in neurons:
            neurons[note_name] = {
                "activation": 1.0 if is_fixed else 0.5,
                "synapses": {},
                "fixed": is_fixed
            }
        
        try:
            text = md_file.read_text(encoding="utf-8")
            links = self._extract_links(text)
            for target in links:
                if target in neurons and target != note_name:
                    neurons[note_name]["synapses"][target] = self._init_vector(note_name, target)
                # Reverse link check
                for other_note, data in neurons.items():
                    if other_note == note_name: continue
                    other_md = self.vault / f"{other_note}.md"
                    if other_md.exists():
                        # In a pulse, we don't want to re-read everything. 
                        # This is a bit expensive, but necessary for liveness.
                        # Optimization: Only check notes that likely link to the new one.
                        pass
                        
            self.save_neurons(neurons)
            logger.info(f"[NeuralCompressor] Integrated new {'FIXED ' if is_fixed else ''}neuron: {note_name}")
            return True
        except Exception as e:
            logger.error(f"[NeuralCompressor] Failed to integrate {note_name}: {e}")
            return False

    def apply_temporal_decay(self, decay_factor: float = 0.995) -> None:
        """
        Subtly reduces activation levels and synaptic weights.
        Simulates 'forgetting' of unused or weak connections.
        Fixed neurons (Guidance/Policy) maintain a persistent floor.
        """
        neurons = self.load_neurons()
        total_pruned = 0
        
        for name, data in neurons.items():
            # 1. Activation Decay
            if data.get("fixed"):
                data["activation"] = max(0.9, data.get("activation", 0.0) * decay_factor)
            else:
                data["activation"] = data.get("activation", 0.0) * decay_factor

            # 2. Synapse Decay
            # Only decay synapses if the neuron is NOT fixed
            if not data.get("fixed"):
                for target in list(data["synapses"].keys()):
                    vec = data["synapses"][target]
                    for i in range(self.dim):
                        vec[i] *= decay_factor
                    
                    if self._vec_magnitude(vec) < 0.05:
                        del data["synapses"][target]
                        total_pruned += 1
                    
        self.save_neurons(neurons)
        if total_pruned > 0:
            logger.info(f"[NeuralCompressor] Temporal decay complete. Pruned {total_pruned} weak synapses.")

    # ─────────────────────────────────────────
    # Output helpers
    # ─────────────────────────────────────────

    def get_cluster_as_markdown(self, cluster: list[str], query_text: str) -> str:
        """Format the compressed cluster as an Obsidian-ready Markdown note."""
        lines = [
            "# Compressed Memory",
            "",
            f"**Query:** {query_text}",
            "",
            f"**Compressed cluster ({len(cluster)} neurons):**",
            "",
        ]
        lines += [f"- [[{note}]]" for note in cluster]
        return "\n".join(lines)

    # ─────────────────────────────────────────
    # Phase 2 extensions
    # ─────────────────────────────────────────

    def increase_dimensions(self, new_dim: int = 8) -> None:
        """
        Upgrade all existing synapse vectors to new_dim by padding with 0.5.
        Call once; neurons.json is updated in-place.
        """
        if new_dim <= self.dim:
            logger.warning(f"Already at {self.dim}D — no upgrade needed.")
            return
        neurons = self.load_neurons()
        for data in neurons.values():
            for target in data.get("synapses", {}):
                vec = data["synapses"][target]
                while len(vec) < new_dim:
                    vec.append(0.5)
        self.dim = new_dim
        self.save_neurons(neurons)
        logger.info(f"[NeuralCompressor] Upgraded to {new_dim}D vectors.")

    def auto_tag_axioms(self, folder: str = "axioms") -> None:
        """
        Any .md file inside vault/axioms/ is auto-tagged as fixed=True.
        Fixed neurons act as permanent anchors — never pruned.
        """
        axiom_dir = self.vault / folder
        if not axiom_dir.exists():
            logger.info(f"[NeuralCompressor] No axioms folder at {axiom_dir}")
            return
        neurons = self.load_neurons()
        tagged = []
        for md in axiom_dir.glob("*.md"):
            name = md.stem
            if name in neurons:
                neurons[name]["fixed"] = True
                tagged.append(name)
            else:
                # Create a stub neuron for the axiom
                neurons[name] = {"activation": 0.0, "synapses": {}, "fixed": True}
                tagged.append(name)
        self.save_neurons(neurons)
        logger.info(f"[NeuralCompressor] Axioms tagged: {tagged}")
