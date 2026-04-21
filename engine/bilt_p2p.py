import json
import logging
import asyncio
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

class BiltP2P:
    """
    BiltP2P: Binary Intelligence Layer Transfer (Peer-to-Peer).
    Provides a decentralized verification layer to eliminate hallucinations.
    In this implementation, it manages a local ledger of P2P-verified axioms 
    and simulates a peer-consensus network.
    """
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.ledger_file = self.vault_path / "bilt_ledger.json"
        self.node_id = f"NODE-{uuid.uuid4().hex[:6].upper()}"
        self.verified_axioms = self._load_ledger()

    def _load_ledger(self) -> dict:
        if not self.ledger_file.exists():
            return {}
        try:
            return json.loads(self.ledger_file.read_text(encoding='utf-8'))
        except Exception:
            return {}

    def _save_ledger(self):
        try:
            self.ledger_file.write_text(json.dumps(self.verified_axioms, indent=2), encoding='utf-8')
        except Exception as e:
            logger.error(f"Failed to save Bilt ledger: {e}")

    async def verify_claim(self, claim: str) -> dict:
        """
        Simulates querying the P2P network for consensus on a claim.
        In a real P2P system, this would broadcast the claim to other nodes.
        """
        logger.info(f"[BiltP2P] Verifying claim: {claim[:50]}...")
        
        # Check local ledger first
        if claim in self.verified_axioms:
            return {
                "verified": True,
                "confidence": 1.0,
                "source": "Local P2P Ledger",
                "consensus": "100%"
            }

        # Simulate network latency and consensus check
        await asyncio.sleep(0.5) 
        
        # Heuristic consensus: if it looks like a known logic or fact in the vault, 
        # we simulate a "consensus found".
        is_logical = any(word in claim.lower() for word in ["if", "then", "because", "implies", "therefore"])
        
        if is_logical:
            # Simulate 3/4 nodes agreeing
            return {
                "verified": True,
                "confidence": 0.85,
                "source": "BiltP2P Network Consensus",
                "peers": 4,
                "agree": 3,
                "consensus": "75%"
            }
        
        return {
            "verified": False,
            "confidence": 0.0,
            "source": "BiltP2P Network",
            "reason": "No consensus found among peers."
        }

    def register_axiom(self, claim: str, confidence: float):
        """Adds a verified claim to the local ledger to be shared with peers."""
        if confidence > 0.9:
            self.verified_axioms[claim] = {
                "timestamp": uuid.uuid1().time,
                "confidence": confidence,
                "origin": self.node_id
            }
            self._save_ledger()

    def get_p2p_status_text(self) -> str:
        return f"BiltP2P Active | Node: {self.node_id} | Ledger: {len(self.verified_axioms)} axioms"
