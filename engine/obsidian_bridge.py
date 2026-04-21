import os
import re
import time

class ObsidianBridge:
    """
    Programmatic bridge to read/write properly formatted Markdown files to the OS Vault.
    """
    def __init__(self, vault_path: str):
        self.vault_path = vault_path
        if not os.path.exists(self.vault_path):
            os.makedirs(self.vault_path)
            
    def write_node(self, node_id: str, tags: list, parent_nodes: list, content: str, node_type="reasoning_node", metadata: dict = None):
        """Writes a compliant markdown file to the vault with multi-dimensional YAML frontmatter."""
        properties = f"---\n"
        properties += f"id: {node_id}\n"
        properties += f"type: {node_type}\n"
        properties += f"status: unconfirmed\n"
        properties += f"parent_nodes: {parent_nodes}\n"
        
        # Multi-dimensional properties
        if metadata:
            for key, value in metadata.items():
                if isinstance(value, list):
                    properties += f"{key}:\n"
                    for item in value:
                        properties += f"  - {item}\n"
                else:
                    properties += f"{key}: {value}\n"
                    
        properties += f"tags:\n"
        for t in tags:
            properties += f"  - {t}\n"
        properties += f"---\n\n"
        
        full_content = properties + content
        
        file_path = os.path.join(self.vault_path, f"{node_id}.md")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(full_content)
        
        return file_path
        
    def read_node(self, node_id: str):
        file_path = os.path.join(self.vault_path, f"{node_id}.md")
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        return None

    def list_all_notes(self) -> list:
        """Returns stem names of all .md files in the vault (excludes system files)."""
        _skip = {"query", "compressed-memory"}
        notes = []
        for fn in os.listdir(self.vault_path):
            if fn.endswith(".md") and fn.replace(".md", "") not in _skip:
                notes.append(fn.replace(".md", ""))
        return notes

    def extract_links(self, note_id: str) -> list:
        """Parses all [[Target]] wikilinks from a note's body. Returns list of target stems."""
        content = self.read_node(note_id)
        if not content:
            return []
        targets = []
        for part in content.split("[[")[1:]:
            if "]]" in part:
                raw = part.split("]]")[0].strip()
                target = raw.split("|")[0].strip()  # Handle [[Target|Alias]]
                if target:
                    targets.append(target)
        return targets
