import logging
import os
from pathlib import Path
from core_engine.obsidian_bridge import ObsidianBridge
from core_engine.neural_compressor import NeuralCompressor

logger = logging.getLogger("InstructorManifold")

class InstructorManifold:
    """
    Manages the Axiom Genome Adjustment loop.
    Instructors guide the evolution of the system's logical genome.
    """
    def __init__(self, vault_path: str, llm=None):
        self.vault_path = Path(vault_path)
        self.obsidian = ObsidianBridge(str(self.vault_path))
        self.compressor = NeuralCompressor(str(self.vault_path))
        self.llm = llm

    def scan_for_feedback(self):
        """
        Scans all HYP- and AXIOM- notes for Instructor feedback.
        Performs Genome Adjustment based on [[APPROVE]], [[REJECT]], or [[CORRECT]].
        """
        hyp_files = list(self.vault_path.glob("HYP-*.md"))
        axiom_files = list(self.vault_path.glob("AXIOM-*.md"))
        
        logger.info(f"InstructorManifold scanning for genome adjustment cues...")

        for f in hyp_files + axiom_files:
            node_id = f.stem
            content = self.obsidian.read_node(node_id)
            if not content: continue

            if "[[APPROVE]]" in content.upper():
                self.promote_to_axiom(node_id, content)
            elif "[[CORRECT]]" in content.upper() and self.llm:
                self.adjust_genome(node_id, content)
            elif "[[REJECT]]" in content.upper():
                self.prune_node(node_id, "Instructor rejection.")

    async def adjust_genome(self, node_id: str, content: str):
        """
        Performs a logical mutation on an Axiom/Hypothesis based on Instructor correction.
        """
        logger.info(f"Adjusting Genome for {node_id}...")
        
        # Extract the correction block
        correction = ""
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if "[[CORRECT]]" in line.upper():
                correction = "\n".join(lines[i+1:])
                break
        
        if not correction:
            logger.warning(f"Found [[CORRECT]] in {node_id} but no correction text found below it.")
            return

        # LLM Synthesis of Adjusted Axiom
        prompt = (
            f"You are adjusting the system's Axiom Genome.\n"
            f"CURRENT AXIOM:\n{content}\n\n"
            f"INSTRUCTOR CORRECTION:\n{correction}\n\n"
            "Synthesize a new version of this Axiom that incorporates the correction while maintaining Parsimony.\n"
            "Respond ONLY with the updated Markdown content."
        )
        
        new_content = await self.llm.generate_response(prompt)
        if new_content:
            # Update the file with the new 'genome'
            self.obsidian.write_node(
                node_id=node_id,
                content=new_content,
                # Metadata remains similar but versioned
            )
            logger.info(f"Genome adjustment complete for {node_id}. New version integrated.")

    def promote_to_axiom(self, node_id: str, content: str):
        """
        Promotes a hypothesis to a verified Axiom (Genome Stabilization).
        """
        if node_id.startswith("AXIOM-"): return # Already promoted

        logger.info(f"Stabilizing Genome: Promoting {node_id} to AXIOM...")
        
        # 1. Update metadata
        new_id = node_id.replace("HYP-", "AXIOM-")
        new_content = content.replace("status: draft", "status: verified")
        new_content = new_content.replace("# Student Hypothesis", "# System Axiom")
        new_content = new_content.replace("## TEACHER FEEDBACK REQUIRED", "## INSTRUCTOR VERIFIED ✅")
        
        # 2. Write as Axiom
        self.obsidian.write_node(
            node_id=new_id,
            tags=["layer/axiom", "verified", "genome/stable"],
            content=new_content,
            node_type="axiom_node"
        )
        
        # 3. Clean up
        self.prune_node(node_id, "Promoted to Axiom.")
        
        # 4. Fix in Synaptic Field
        self.compressor.integrate_new_note(new_id)
        neurons = self.compressor.load_neurons()
        if new_id in neurons:
            neurons[new_id]["fixed"] = True
            neurons[new_id]["activation"] = 1.0
            self.compressor.save_neurons(neurons)

    def prune_node(self, node_id: str, reason: str):
        """
        Prunes a rejected or obsolete node from the genome.
        """
        logger.info(f"Pruning {node_id} from genome: {reason}")
        try:
            filename = f"{node_id}.md"
            # Check multiple potential folders
            for folder in ["", "hypotheses", "guidance"]:
                p = self.vault_path / folder / filename
                if p.exists():
                    p.unlink()
                    break
            
            neurons = self.compressor.load_neurons()
            if node_id in neurons:
                del neurons[node_id]
                self.compressor.save_neurons(neurons)
        except Exception as e:
            logger.error(f"Failed to prune {node_id}: {e}")

if __name__ == "__main__":
    import sys
    desk = TeacherDesk(sys.argv[1] if len(sys.argv) > 1 else "./Vault")
    desk.scan_for_approvals()
