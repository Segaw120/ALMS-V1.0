import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class PolicyEngine:
    """
    Loads and manages reasoning and knowledge policies from the Vault.
    Ensures that AI behavior adheres to organizational methodology and constraints.
    """
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.policy_dir = self.vault_path / "policies"
        self.policies = []
        self.load_policies()

    def load_policies(self):
        """Discovers all markdown policies in the policy directory."""
        if not self.policy_dir.exists():
            self.policy_dir.mkdir(parents=True, exist_ok=True)
            return

        self.policies = []
        for policy_file in self.policy_dir.glob("*.md"):
            try:
                content = policy_file.read_text(encoding='utf-8')
                self.policies.append({
                    "id": policy_file.stem,
                    "content": self._strip_frontmatter(content)
                })
            except Exception as e:
                logger.error(f"Failed to load policy {policy_file}: {e}")

    def get_active_policies_text(self) -> str:
        """Returns a concatenated string of all active policies for scaffold injection."""
        if not self.policies:
            return "No specific organizational policies active."

        lines = ["[ORGANIZATIONAL POLICIES & METHODOLOGY]"]
        for p in self.policies:
            lines.append(f"\n  Policy: {p['id']}")
            for ln in p['content'].splitlines():
                if ln.strip():
                    lines.append(f"  | {ln.strip()}")
        return "\n".join(lines)

    @staticmethod
    def _strip_frontmatter(text: str) -> str:
        if text.startswith("---"):
            end = text.find("---", 3)
            if end != -1:
                return text[end + 3:].strip()
        return text.strip()
