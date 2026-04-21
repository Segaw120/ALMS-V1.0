import time
import logging
import os
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from core_engine.neural_compressor import NeuralCompressor
from core_engine.governor import MetaGovernor
from core_engine.llm_manager import LLMManager
from core_engine.prompt_compressor import PromptCompressor
from core_engine.auto_researcher import AutoResearcher
from core_engine.logic_validator import LogicValidator
from core_engine.obsidian_bridge import ObsidianBridge
from core_engine.memory_manager import MemoryManager
from learning_engine.instructor_manifold import InstructorManifold

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler("pulse.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SystemPulse")

class VaultHandler(FileSystemEventHandler):
    def __init__(self, compressor: NeuralCompressor):
        self.compressor = compressor

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(".md"):
            note_name = Path(event.src_path).stem
            logger.info(f"New note detected: {note_name}. Integrating...")
            self.compressor.integrate_new_note(note_name)

    def on_modified(self, event):
        # We could re-integrate on modification if we wanted to update synapses
        pass

class SystemPulse:
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.llm = LLMManager()
        self.obsidian = ObsidianBridge(str(self.vault_path))
        self.validator = LogicValidator(self.llm)
        self.researcher = AutoResearcher(self.llm, self.obsidian, self.validator)
        self.memory = MemoryManager(vault_path=str(self.vault_path))
        self.prompt_compressor = PromptCompressor(
            vault_path=str(self.vault_path),
            obsidian=self.obsidian,
            researcher=self.researcher
        )
        
        self.compressor = self.memory.compressor
        self.governor = MetaGovernor(str(self.vault_path), self.llm)
        self.instructor_manifold = InstructorManifold(str(self.vault_path), self.llm)
        self.observer = Observer()
        
    async def start(self):
        logger.info(f"System Pulse starting. Monitoring: {self.vault_path}")
        
        # 1. Start Vault Watcher
        event_handler = VaultHandler(self.compressor)
        self.observer.schedule(event_handler, str(self.vault_path), recursive=True)
        self.observer.start()
        
        try:
            # 2. Continuous Evolution Loop
            while True:
                # A. Hebbian Drift (Temporal Decay)
                logger.info("[Pulse] Applying Hebbian Drift...")
                self.compressor.apply_temporal_decay(decay_factor=0.998)
                
                # B. Meta-Governor Expansion Cycle
                logger.info("[Pulse] Triggering Meta-Governor Expansion Cycle...")
                await self.governor.run_expansion_cycle(
                    pc=self.prompt_compressor,
                    researcher=self.researcher,
                    llm=self.llm
                )
                
                # C. Instructor Manifold Scan (Genome Adjustment)
                logger.info("[Pulse] Scanning for Instructor Guidance...")
                self.instructor_manifold.scan_for_feedback()

                # D. Self-Audit
                await self.governor.self_audit(self.governor.refactorer)
                
                # Sleep between pulses (e.g., 5 minutes)
                logger.info("[Pulse] Sleeping for 300s...")
                await asyncio.sleep(300) 
        except Exception as e:
            logger.error(f"[Pulse] Error in evolution loop: {e}")
        finally:
            self.observer.stop()
            self.observer.join()

if __name__ == "__main__":
    import asyncio
    # Get vault path relative to this script
    current_dir = Path(__file__).parent.parent
    vault_dir = current_dir / "Vault"
    
    pulse = SystemPulse(str(vault_dir))
    asyncio.run(pulse.start())
