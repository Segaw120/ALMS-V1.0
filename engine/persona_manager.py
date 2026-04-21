import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class PersonaManager:
    """
    Manages the 'Self' of the system.
    Decouples identity from core logic. If no SELF.md exists, the system is 'non-self'.
    """
    def __init__(self, vault_path: str):
        self.vault_path = vault_path
        self.identity_path = os.path.join(vault_path, "identity", "SELF.md")
        self.templates_path = os.path.join(vault_path, "templates")
        self.persona_name = "Non-Self (Logic Engine)"
        self.active_profile = "none"
        self.load_persona()

    def load_persona(self):
        """Loads the persona from SELF.md if it exists."""
        self.persona_content = "" # Default to empty
        if not os.path.exists(self.identity_path):
            self.persona_name = "Non-Self (Logic Engine)"
            return

        try:
            with open(self.identity_path, "r", encoding="utf-8") as f:
                content = f.read()
                self.persona_content = content
                # Simple extraction of the first H1 as persona name
                import re
                match = re.search(r"^# (.*)", content, re.MULTILINE)
                if match:
                    self.persona_name = match.group(1).strip()
                else:
                    self.persona_name = "Custom Persona"
        except Exception as e:
            logger.error(f"Failed to load persona: {e}")
            self.persona_name = "Error Loading Persona"

    def switch_profile(self, profile: str):
        """
        Switches the system profile by deploying templates.
        profile: 'student', 'researcher', or 'organization'
        """
        profile = profile.lower()
        identity_template = os.path.join(self.templates_path, "identity", f"{profile}.md")
        policy_templates_dir = os.path.join(self.templates_path, "policies")

        if not os.path.exists(identity_template):
            logger.error(f"Profile template not found: {identity_template}")
            return False

        try:
            # 1. Update Identity
            with open(identity_template, "r", encoding="utf-8") as f:
                content = f.read()
            
            os.makedirs(os.path.dirname(self.identity_path), exist_ok=True)
            with open(self.identity_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            # 2. Update Policies
            policy_dest_dir = os.path.join(self.vault_path, "policies")
            os.makedirs(policy_dest_dir, exist_ok=True)
            
            # Clear existing active policies to avoid profile mixing
            for f in os.listdir(policy_dest_dir):
                if f.endswith(".md"):
                    os.remove(os.path.join(policy_dest_dir, f))
            
            # Find and copy matching policy template
            import shutil
            for f in os.listdir(policy_templates_dir):
                if f.startswith(profile) and f.endswith(".md"):
                    shutil.copy(
                        os.path.join(policy_templates_dir, f),
                        os.path.join(policy_dest_dir, f)
                    )
            
            self.active_profile = profile
            self.load_persona()
            logger.info(f"Switched to profile: {profile} (Identity: {self.persona_name})")
            return True
        except Exception as e:
            logger.error(f"Failed to switch profile: {e}")
            return False

    def get_persona_scaffold(self) -> str:
        """Returns the persona framing for scaffold injection."""
        lines = [
            f"[SYSTEM IDENTITY: {self.persona_name}]",
            "  The following behavioral constraints and tone directives are active:",
        ]
        for ln in self.persona_content.splitlines():
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
