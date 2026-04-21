"""
self_refactorer.py
==================
The Self-Evolution Engine. Allows the system to refactor its own source code.
"""

import os
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

class SelfRefactorer:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.core_path = self.base_path / "core_engine"
        self.backup_path = self.base_path / "backups" / "core_engine"
        
        if not self.backup_path.exists():
            self.backup_path.mkdir(parents=True, exist_ok=True)

    def backup_core(self):
        """Creates a timestamped backup of the core_engine."""
        import shutil
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = self.backup_path / f"core_backup_{ts}"
        shutil.copytree(self.core_path, dest)
        logger.info(f"[SelfRefactorer] Backup created at {dest}")
        return dest

    def apply_refactor(self, filename: str, new_content: str):
        """
        Applies a code change to a core_engine file.
        Mandatory: Runs a syntax check before overwriting.
        """
        target_file = self.core_path / filename
        if not target_file.exists():
            logger.error(f"[SelfRefactorer] Target file {filename} does not exist.")
            return False

        # Pre-validation: Syntax check
        temp_file = target_file.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(new_content)
        
        try:
            subprocess.run(["python", "-m", "py_compile", str(temp_file)], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"[SelfRefactorer] Refactor FAILED syntax check: {e.stderr.decode()}")
            os.remove(temp_file)
            return False

        # Apply change
        self.backup_core()
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(new_content)
        
        os.remove(temp_file)
        logger.info(f"[SelfRefactorer] Refactored {filename} successfully.")
        return True

    def rollback(self):
        """
        Reverts the core_engine to the most recent backup.
        """
        import shutil
        backups = sorted(self.backup_path.glob("core_backup_*"))
        if not backups:
            logger.error("[SelfRefactorer] No backups found for rollback.")
            return False
        
        latest_backup = backups[-1]
        logger.warning(f"[SelfRefactorer] TRIGGERING ROLLBACK to {latest_backup}...")
        
        # Clear current core (carefully) and restore
        shutil.rmtree(self.core_path)
        shutil.copytree(latest_backup, self.core_path)
        
        logger.info("[SelfRefactorer] Rollback COMPLETE.")
        return True

    def detect_limitations(self, logs: list):
        """
        Analyzes research logs to find architectural weaknesses.
        Returns a prompt for the LLM to generate a refactor.
        """
        # Logic to scan logs for "TimeoutError", "MemoryError", etc.
        pass
