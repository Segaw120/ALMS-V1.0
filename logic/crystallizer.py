import json
import logging
import os
from pathlib import Path
from typing import List, Dict, Set
from core_engine.llm_manager import LLMManager
from core_engine.obsidian_bridge import ObsidianBridge
from core_engine.neural_compressor import NeuralCompressor

logger = logging.getLogger("Crystallizer")

class Crystallizer:
    """
    Implements Lossless Structural Compression.
    Identifies tight clusters in the synaptic field and synthesizes
    higher-order 'Theory' nodes (Layer 1) to represent them.
    """
    def __init__(self, vault_path: str, llm: LLMManager):
        self.vault_path = Path(vault_path)
        self.llm = llm
        self.obsidian = ObsidianBridge(str(self.vault_path))
        self.compressor = NeuralCompressor(str(self.vault_path))
        self.neurons_file = self.vault_path / "neurons.json"

    def find_clusters(self, threshold: float = 0.7) -> List[Set[str]]:
        """
        Identifies clusters of notes that are strongly linked.
        Uses a simple connected-components approach on high-weight synapses.
        """
        if not self.neurons_file.exists():
            return []

        with open(self.neurons_file, "r", encoding="utf-8") as f:
            neurons = json.load(f)

        adj = {}
        for source, data in neurons.items():
            adj[source] = set()
            for target, vec in data.get("synapses", {}).items():
                # Magnitude check for "tightness"
                mag = sum(x*x for x in vec)**0.5
                if mag > threshold:
                    adj[source].add(target)

        # Find connected components (undirected for clustering)
        visited = set()
        clusters = []
        
        for node in adj:
            if node not in visited:
                cluster = set()
                stack = [node]
                while stack:
                    curr = stack.pop()
                    if curr not in visited:
                        visited.add(curr)
                        cluster.add(curr)
                        # Add neighbors from adj (both directions if exists)
                        if curr in adj:
                            stack.extend(adj[curr])
                        # Check reverse links
                        for potential_source, targets in adj.items():
                            if curr in targets:
                                stack.append(potential_source)
                
                if len(cluster) >= 3: # Only cluster 3+ nodes
                    clusters.append(cluster)
        
        return clusters

    async def crystallize_cluster(self, cluster: Set[str]):
        """
        Synthesizes a cluster into a Layer 1 Theory node.
        Lossless: Maintains links to all constituent Layer 0 nodes.
        """
        cluster_list = list(cluster)
        logger.info(f"Crystallizing cluster of {len(cluster)} nodes: {cluster_list[:5]}...")

        # 1. Gather context from constituent nodes
        contexts = []
        for node in cluster_list:
            content = self.obsidian.read_node(node)
            if content:
                contexts.append(f"--- Node: {node} ---\n{content}")

        full_context = "\n\n".join(contexts)

        # 2. LLM Synthesis (Parsimonious)
        system_prompt = (
            "You are the ALMS Crystallizer. Your job is PARSIMONIOUS COMPRESSION.\n"
            "Assume the provided cluster has an underlying simple structure (a 'Straight Line' in logic space).\n"
            "Synthesize a 'Layer 1 Theory' that captures this essence while ignoring noise.\n"
            "Your output must be a mathematical-style deduction of First Principles (Axioms).\n"
            "CRITICAL: Be minimal. Every word must reduce the coding rate of the data."
        )
        
        prompt = f"Identify the low-dimensional manifold (First Principles) of this cluster:\n\n{full_context[:10000]}"
        theory_content = await self.llm.generate_response(f"{system_prompt}\n\n{prompt}")

        if not theory_content:
            logger.error("LLM failed to generate theory content.")
            return

        # 3. Self-Consistency Audit
        is_consistent = await self.audit_theory(theory_content, cluster_list)
        if not is_consistent:
            logger.warning(f"Theory synthesis for cluster {cluster_list[:3]} failed Self-Consistency Audit. Pruning.")
            return None

        # 4. Create the Hypothesis (Student's Draft)
        hyp_id = f"HYP-{os.urandom(3).hex().upper()}"
        
        # Add references to constituent nodes (Lossless)
        theory_content = (
            f"--- status: draft | layer: theory | student_confidence: {0.85} ---\n"
            f"# Student Hypothesis: {hyp_id}\n\n"
            f"{theory_content}\n\n"
            "## Constituent Evidence (Layer 0)\n"
            + "\n".join([f"- [[{node}]]" for node in cluster_list])
            + "\n\n## TEACHER FEEDBACK REQUIRED\n"
            "Please review this manifold. Does it accurately capture the First Principles of the cluster?\n"
            "Respond with [[APPROVE]] or [[REJECT]] and corrections."
        )

        self.obsidian.write_node(
            node_id=hyp_id,
            tags=["layer/theory", "crystallized", "ma/parsimonious", "status/draft"],
            parent_nodes=cluster_list,
            content=theory_content,
            node_type="theory_node"
        )

        # 5. Integrate as a "Weak" neuron (Hypothesis)
        self.compressor.integrate_new_note(hyp_id)
        
        logger.info(f"Hypothesis staged for Teacher review: {hyp_id}")
        return hyp_id

    async def audit_theory(self, theory: str, cluster: List[str]) -> bool:
        """
        Reconstruction Test: Can the theory explain the constituent nodes?
        """
        logger.info(f"Auditing theory self-consistency against {len(cluster)} nodes...")
        
        # Sample 2 random nodes for reconstruction test
        import random
        samples = random.sample(cluster, min(2, len(cluster)))
        
        audit_prompt = (
            "You are a Logic Auditor. Given a 'Theory' (First Principles), "
            "can the following 'Evidence' be logically deduced or reconstructed from it?\n\n"
            f"THEORY:\n{theory}\n\n"
            f"EVIDENCE SAMPLES:\n" + "\n".join([f"- {s}" for s in samples]) + "\n\n"
            "Respond ONLY with 'CONSISTENT' or 'INCONSISTENT' and a 1-sentence reason."
        )
        
        result = await self.llm.generate_response(audit_prompt)
        if result and "CONSISTENT" in result.upper() and "INCONSISTENT" not in result.upper():
            return True
        return False

    async def run_crystallization_cycle(self):
        """Runs a full pass of cluster detection and stages new Hypotheses."""
        clusters = self.find_clusters()
        logger.info(f"Found {len(clusters)} potential clusters for crystallization.")
        
        new_hyps = []
        for cluster in clusters:
            hyp_id = await self.crystallize_cluster(cluster)
            if hyp_id:
                new_hyps.append(hyp_id)
        
        # Proactively report the new hypotheses to the Teacher
        if new_hyps:
            from core_engine.reporter import reporter
            await reporter.log_event("STUDENT_REPORT", {
                "message": "I have synthesized new Hypotheses from experience clusters. Please review them at the Teacher's Desk.",
                "hypotheses": new_hyps
            })

if __name__ == "__main__":
    import asyncio
    # Simple test run logic could go here
    pass
