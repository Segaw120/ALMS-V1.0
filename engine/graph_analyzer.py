import os
import networkx as nx
import logging
import asyncio
from typing import List, Dict, Tuple
from core_engine.llm_manager import LLMManager
from core_engine.obsidian_bridge import ObsidianBridge
from core_engine.logic_validator import LogicValidator

class GraphAnalyzer:
    """
    Parses the Obsidian Vault into a deterministic Knowledge Graph.
    Uses LLM-based Vector Clustering to identify 'High-Nuance Paths'
    by measuring semantic distances between conceptually diverse nodes.
    """
    def __init__(self, llm: LLMManager, obsidian: ObsidianBridge, validator: LogicValidator):
        self.llm = llm
        self.obsidian = obsidian
        self.validator = validator
        self.graph = nx.DiGraph()

    def build_graph_from_vault(self):
        """Scans the vault, parses YAML frontmatter, and builds a directed graph."""
        self.graph.clear()
        
        for filename in os.listdir(self.obsidian.vault_path):
            if not filename.endswith('.md'):
                continue
                
            file_path = os.path.join(self.obsidian.vault_path, filename)
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Naive metadata extraction for speed; in production use pyyaml
            node_id = filename.replace('.md', '')
            
            # Extract parent nodes using regex
            import re
            parent_match = re.search(r'parent_nodes:\s*\[(.*?)\]', content)
            parents = []
            if parent_match and parent_match.group(1).strip():
                # Handle either ['ID'] or [ID] format
                raw_parents = parent_match.group(1).split(',')
                parents = [p.strip().strip("'").strip('"') for p in raw_parents]
                
            # Extract vector clusters
            cluster_match = re.search(r'vector_clusters:(.*?)\n\w', content, re.DOTALL)
            clusters = []
            if cluster_match:
                cluster_lines = cluster_match.group(1).strip().split('\n')
                clusters = [line.replace('- ', '').strip() for line in cluster_lines if line.strip()]

            # Add logic node
            self.graph.add_node(node_id, clusters=clusters, content=content)
            
            # Add directed edges from parents -> child
            for p in parents:
                if p:
                    self.graph.add_edge(p, node_id)
                    
        logging.info(f"Graph Built: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges.")

    async def calculate_semantic_distance(self, node_a: str, node_b: str) -> float:
        """
        Uses the LLM to calculate Vector Clustering semantic distance.
        Returns a Nuance Score (0.0 to 1.0) indicating how disparate the topics are.
        """
        data_a = self.graph.nodes[node_a].get('clusters', [])
        data_b = self.graph.nodes[node_b].get('clusters', [])
        
        # If nodes have no distinct cluster data, fallback gracefully
        if not data_a and not data_b:
             return 0.1
             
        system_prompt = (
            "You are a conceptual distance evaluator. "
            "Evaluate the semantic vector space distance between Topic A and Topic B. "
            "0.0 = Almost identical logic spaces (Lineal). "
            "1.0 = Wildly disconnected logic spaces bridging a massive gap (High Nuance). "
            "Respond ONLY with a float between 0.0 and 1.0."
        )
        
        prompt = f"Topic A clusters: {data_a}\nTopic B clusters: {data_b}\n\nOutput only the numeric distance score."
        response = await self.llm.generate_response(f"{system_prompt}\n\n{prompt}")
        
        try:
            return float(response.strip())
        except ValueError:
            logging.warning("Failed to parse semantic distance. Defaulting to 0.5")
            return 0.5

    async def identify_nuanced_paths(self):
        """
        Finds all paths and scores them by their average semantic leaps.
        Identifies the logical structure needed for RL Scaffold Rewards.
        """
        # Find roots (in-degree 0) and leaves (out-degree 0)
        roots = [n for n, d in self.graph.in_degree() if d == 0]
        leaves = [n for n, d in self.graph.out_degree() if d == 0]
        
        high_nuance_paths = []
        
        # Traverse all possible complete paths
        for root in roots:
            for leaf in leaves:
                for path in nx.all_simple_paths(self.graph, root, leaf):
                    # Calculate cumulative semantic leap across the path edges
                    total_nuance = 0
                    for i in range(len(path) - 1):
                        leap_score = await self.calculate_semantic_distance(path[i], path[i+1])
                        total_nuance += leap_score
                        
                    avg_nuance = total_nuance / max(1, (len(path) - 1))
                    
                    if avg_nuance > 0.65:  # Nuance Threshold
                        high_nuance_paths.append({
                            "path": path,
                            "nuance_score": avg_nuance
                        })
                        
        # Sort by most nuanced path
        high_nuance_paths.sort(key=lambda x: x['nuance_score'], reverse=True)
        return high_nuance_paths

    async def pipe_to_evaluation_pipeline(self):
        """
        Takes the highest nuance paths found by Vector Clustering and 
        pushes them to the LogicValidator and RL Simulation queue for empirical confirmation.
        """
        self.build_graph_from_vault()
        logging.info("Evaluating graph for high-nuance paths through LLM semantic clustering...")
        
        paths = await self.identify_nuanced_paths()
        
        results = []
        for p in paths[:3]: # Evaluate Top 3 paths
            path_nodes = p['path']
            # Stitch the holistic reasoning path together
            full_path_context = "\n".join([self.graph.nodes[n]['content'] for n in path_nodes])
            
            # Send to evaluation pipeline
            evaluation_result = await self.validator.evaluate_reasoning(
                reasoning_content=f"Path Traversal: {' -> '.join(path_nodes)}",
                context=full_path_context
            )
            
            results.append({
                "path": path_nodes,
                "nuance_score": p['nuance_score'],
                "validation": evaluation_result
            })
            
        return results
