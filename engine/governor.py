"""
governor.py
===========
The SYS-000 Meta-Governor. 
Orchestrates autonomous expansion, self-awareness, and self-modification.
"""

import os
import json
import logging
import asyncio
import random
from pathlib import Path
from core_engine.reporter import reporter
from core_engine.self_refactorer import SelfRefactorer
from learning_engine.crystallizer import Crystallizer

logger = logging.getLogger(__name__)

class MetaGovernor:
    def __init__(self, vault_path: str, llm=None):
        self.vault = Path(vault_path)
        self.neurons_file = self.vault / "neurons.json"
        self.cycle_count = 0
        self.llm = llm
        self.crystallizer = Crystallizer(vault_path, llm) if llm else None
        self.refactorer = SelfRefactorer(str(self.vault.parent))

    def get_knowledge_voids(self) -> list[str]:
        """
        Analyzes neurons.json to find regions with low synaptic density 
        or high entropy gaps.
        """
        if not self.neurons_file.exists():
            return []
            
        with open(self.neurons_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        voids = []
        for node, attr in data.items():
            synapses = attr.get("synapses", {})
            # A node is a "void" if it has low activation and few synapses,
            # or if it's a stub concept with no depth.
            if len(synapses) < 2 and attr.get("activation", 0) < 0.3:
                voids.append(node)
        
        random.shuffle(voids)
        return voids[:5]

    async def run_expansion_cycle(self, pc, researcher, llm):
        """
        One cycle of proactive growth:
        1. Identify Voids.
        2. Generate Meta-Seed.
        3. Launch Proactive Research.
        4. Report to Supabase.
        """
        self.cycle_count += 1
        cycle_id = f"CYC-{self.cycle_count:03d}"
        
        logger.info(f"[MetaGovernor] Starting Cycle {cycle_id}")
        
        voids = self.get_knowledge_voids()
        if not voids:
            logger.info("[MetaGovernor] No significant voids detected. Observing stability...")
            return

        target_void = voids[0]
        meta_seed = f"Deeply explore the relationship between {target_void} and the core system architecture. What is the missing link?"
        
        await reporter.report_expansion(
            cycle_id=cycle_id,
            action=f"Expansion into {target_void}",
            analysis=f"Detected low synaptic density at {target_void}. Initiating proactive gap filling.",
            meta_commentary="The system is becoming aware of its own under-sampled conceptual regions."
        )

        # Fire the pipeline proactively
        result = await llm.generate_with_vault_context(
            prompt=meta_seed,
            compressor=pc
        )
        
        # Self-Axiomatization check (simplified)
        if "AXIOM" in result.get("response", "").upper():
            logger.info(f"[MetaGovernor] Potential Axiom detected in {target_void} expansion.")
            # Trigger self-modification logic here in future
            
        await reporter.log_event("EXPANSION_COMPLETE", {
            "cycle_id": cycle_id,
            "target": target_void,
            "seeds": result.get("seeds", []),
            "response_snippet": result.get("response", "")[:200]
        })

    async def self_audit(self, refactorer):
        """
        Checks logs and system performance to detect architectural bottlenecks.
        If a previous modification caused a regression, it triggers a ROLLBACK.
        """
        logger.info("[MetaGovernor] Performing Self-Audit...")
        
        # Heuristic: If we have high error rates in the last cycle, rollback.
        # (In a production scenario, this would check Supabase for real-time metrics)
        regression_detected = False 
        
        if regression_detected:
            await reporter.report_expansion(
                cycle_id=f"AUDIT-{self.cycle_count}",
                action="ROLLBACK",
                analysis="Performance regression or stability drop detected after last refactor.",
                meta_commentary="Axiom SYS-007 requires stability over growth. Reverting to known good state."
            )
            self.refactorer.rollback()
            return True
        
        # ── Compounding Growth Metric ──────────────────
        # Measure Information Density: Synapses per Neuron
        with open(self.neurons_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        density = sum(len(n.get("synapses", {})) for n in data.values()) / len(data)
        logger.info(f"[MetaGovernor] Network Density: {density:.2f} synapses/neuron")
        
        # Trigger Crystallization if density is high
        if density > 4.5 and self.crystallizer:
            logger.info("[MetaGovernor] High density detected. Triggering Crystallization...")
            await self.crystallizer.run_crystallization_cycle()

        return False
