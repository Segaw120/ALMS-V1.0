import asyncio
import uuid
import re
import logging
from typing import List, Dict

from core_engine.llm_manager import LLMManager
from core_engine.obsidian_bridge import ObsidianBridge
from core_engine.memory_manager import MemoryManager
from core_engine.logic_validator import LogicValidator
from core_engine.auto_researcher import AutoResearcher

class FractalReasoner:
    def __init__(self, llm: LLMManager, obsidian: ObsidianBridge, memory: MemoryManager, validator: LogicValidator, researcher: AutoResearcher):
        self.llm = llm
        self.obsidian = obsidian
        self.memory = memory
        self.validator = validator
        self.researcher = researcher
        self.active_threads = 0
        self.max_depth = 10  # Configurable fractal depth
        self.pruning_threshold = 0.45

    async def start_fractal_thread(self, initial_query: str):
        """
        Roots a new fractal request. Spawns divergent paths.
        E.g., paths probing worst-case risk vs best-case scale.
        """
        base_node_id = f"RN-{uuid.uuid4().hex[:6].upper()}"
        
        # Save root to Obsidian
        self.obsidian.write_node(
            node_id=base_node_id,
            tags=["fractal/root", "branch_spawn"],
            parent_nodes=[],
            content=f"# Root Inquiry\n{initial_query}",
            node_type="reasoning_root"
        )
        
        # Spawn Concurrent Parallel Paths
        prompts = [
            f"Analyze this from a purely systematic, structural defense perspective: {initial_query}",
            f"Analyze this from a chaotic, aggressively scalable venture expansion perspective: {initial_query}"
        ]
        
        tasks = []
        for p in prompts:
            tasks.append(self._reasoning_loop(p, parent_id=base_node_id, depth=0))
            
        # Execute concurrently
        await asyncio.gather(*tasks)

    async def _reasoning_loop(self, semantic_cue: str, parent_id: str, depth: int):
        """
        The Continuous Memory-Stored Stream.
        One thought directly seeds the next, storing linearly in both Memory and Obsidian.
        """
        if depth >= self.max_depth:
            # Reached fractal limit, stop streaming
            return

        self.active_threads += 1
        node_id = f"RN-{uuid.uuid4().hex[:6].upper()}"
        
        try:
            # 1. Chain-of-Thought Generation (Stochastic Vector Clustering)
            system_instruction = (
                "You are the Chaotic Fractal Reasoner. Use structural Chain-of-Thought to map logical extremes.\n"
                "Given the trailing thought, break down the logic exactly as follows:\n\n"
                "1. [Stochastic Divergence]: Propose an extreme, edge-case variable that breaks the current logic.\n"
                "2. [Nuance Synthesis]: How does the logic bend or adapt to accommodate this edge-case?\n"
                "3. [Cluster Domain]: Name two completely distinct conceptual domains this edge-case connects (Format: DomainA & DomainB)."
            )
            response = await self.llm.generate_response(f"{system_instruction}\n\nTrailing Thought: {semantic_cue}")
            
            if not response:
                return
                
            # Parse CoT dimensions
            cluster_domains = []
            nuance_text = response
            
            cluster_match = re.search(r'\[Cluster Domain\]:(.*?)(?:\n|$)', response, re.IGNORECASE)
            if cluster_match:
                domains = [d.strip() for d in cluster_match.group(1).split('&')]
                cluster_domains = [d for d in domains if d]
            
            metadata = {
                "vector_clusters": cluster_domains,
                "nuance_score": 0.85 # Placeholder for embed-distance routing
            }
                
            # 2. Objective Logic Validation
            # We replace the basic _evaluate_route with a deep objective critique
            evaluation = await self.validator.evaluate_reasoning(response, context=semantic_cue)
            score = evaluation.get("score", 0.5)
            testable_hypothesis = evaluation.get("testable_hypothesis")
            
            if score < self.pruning_threshold:
                logging.info(f"Pruned Route {node_id} due to poor logic/consistency. Score: {score}")
                return
                
            # 3. Tag extraction & Status Management
            tags = self._extract_tags(response)
            if testable_hypothesis:
                tags.append("hypothesis/unconfirmed")
                # Trigger Auto-Researcher for Slow Confirmation
                asyncio.create_task(self.researcher.execute_empirical_verification(testable_hypothesis, node_id))
            else:
                tags.append("logic/verified")
            
            # 4. Memory-Stored Support (Streaming Memory Buffer)
            self.memory.store_context(f"[{node_id}] {response}")
            
            # 5. Save to Obsidian
            content = f"# Inference Depth {depth}\n{response}\n\n"
            content += f"## ⚖️ Objective Evaluation\n"
            content += f"- **Logic Score:** `{score}`\n"
            content += f"- **Critique:** {evaluation.get('critique', 'N/A')}\n"
            if evaluation.get("fallacies"):
                content += f"- **Fallacies Detected:** {', '.join(evaluation.get('fallacies'))}\n"
            if testable_hypothesis:
                content += f"- **Verification Required:** {testable_hypothesis}\n"

            self.obsidian.write_node(
                node_id=node_id,
                tags=tags,
                parent_nodes=[parent_id],
                content=content,
                node_type="reasoning_node",
                metadata=metadata
            )
            
            # Infinite recursion (controlled by max_depth and pruning)
            await self._reasoning_loop(semantic_cue=response, parent_id=node_id, depth=depth+1)
            
        finally:
            self.active_threads -= 1

    def _evaluate_route(self, content: str) -> float:
        """
        Deterministic Particle Mechanics (MVP Implementation)
        Evaluates Depth, Logical Consistency, and Novelty based on vector weights.
        """
        # In a production environment, this applies advanced LLM-based 
        # probability scoring or deterministic NLP keyword variance checking.
        score = 0.5
        
        # Penalize short, un-nuanced responses
        if len(content.split()) < 20: 
            score -= 0.2
            
        # Reward complex structural words (Signaling depth)
        complexity_markers = ["therefore", "implies", "exponential", "variance", "bottleneck", "equilibrium"]
        for marker in complexity_markers:
            if marker in content.lower():
                score += 0.05
                
        return min(1.0, score)

    def _extract_tags(self, content: str) -> List[str]:
        """Automatically parses emergent tags using NLP/Regex for Convergence mapping."""
        # Simple extraction of anything looking like #tag
        found_tags = re.findall(r'#(\w+)', content)
        
        # Add basic taxonomy for merging logic later
        base_tags = ["fractal/inference"]
        if "risk" in content.lower(): base_tags.append("taxonomy/risk")
        if "scale" in content.lower(): base_tags.append("taxonomy/scale")
        
        return list(set(base_tags + found_tags))
