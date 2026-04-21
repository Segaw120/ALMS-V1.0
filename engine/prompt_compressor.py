"""
prompt_compressor.py  (v2)
==========================
Full pre-LLM reasoning pipeline with verifiable, traceable reasoning
and inline AutoResearch for knowledge gaps.

PIPELINE:
==========

  User Prompt
      │
      ▼ ─────────────────────────────────────── SYNC (no LLM) ──
  [S0] Governance & Identity
       Load policies from Vault/policies and persona from Vault/identity.
      │
      ▼
  [S1] Seed Extraction
       Tokenize prompt → score against vault neuron stems.
       Hub fallback if nothing matches.
      │
      ▼
  [S2] Hebbian Compression  (4 cycles, fast)
       Fire seeds → propagate cosine-similarity activation → prune weak synapses.
       Returns the minimal cluster of neurons that reconstructs the seed.
      │
      ▼
  [S3] Cluster Retrieval
       Pull actual note bodies from the activated cluster.
       Cap per note to avoid context bloat.
      │
      ▼
  [S4] Gap Analysis
       Diff: (prompt tokens) - (cluster tokens) = uncovered concepts.
      │
      ▼ ─────────────────────────────────────── ASYNC (optional LLM) ──
  [S5] Hypothesis Extraction from Gaps
       Score each gap for "empirical urgency" (length + novelty heuristic).
       High-urgency gaps → form a testable hypothesis for AutoResearch.
      │
      ▼
  [S6] AutoResearch (conditional)
       If gap_urgency > research_threshold → call AutoResearcher.
       Research runs double-blind Python experiments.
       Results written to Vault as EXP-xxxx.md and injected into scaffold.
      │
      ▼
  [S6.5] Human Audit Preparation
       Prepare a structured auditable trail for Human-in-the-Loop verification.
      │
      ▼
  [S7] Reasoning Scaffold
       Assembly of all prior steps into a structured context block:
         [SYSTEM IDENTITY] — Persona-based behavioral framing
         [POLICIES]        — Organizational reasoning constraints
         [KNOWN]           — vault-grounded facts (authoritative)
         [RESEARCHED]      — fresh empirical evidence from AutoResearch
         [P2P VERIFIED]    — distributed consensus on logic/claims
         [CONNECTIONS]     — live synapse map of the recalled cluster
         [GAPS]            — concepts still unresolved (LLM must infer)
         [TRACE]           — full step-by-step audit of this pipeline run
         [INSTRUCTIONS]    — strict directives for zero hallucination
         [USER QUERY]      — the original prompt
      │
      ▼ ─────────────────────────────────────── LLM (slow weights) ──
  LLM receives scaffold → synthesises response
      │
      ▼ ─────────────────────────────────────── ASYNC (no extra LLM) ──
  [S8] Backward Compression
       Co-mentioned neurons → Hebbian reinforce synapses.
       Novel tokens → create stub neurons in neurons.json.
       Every inference makes the vault smarter.
      │
      ▼
  [S9] Trace Persistence
       Full pipeline trace written as TRACE-<id>.md in the Vault.
       Every response has a cryptographic audit trail in Obsidian.

The slow weights are responsible ONLY for:
  - Synthesising pre-loaded vault facts into a coherent response
  - Filling flagged gaps with general knowledge (marked 'Inference:')
  - Response formatting
They are NOT responsible for factual recall or gap research — done above.
"""

import re
import uuid
import logging
import asyncio
from datetime import datetime
from typing import TYPE_CHECKING

from core_engine.neural_compressor import NeuralCompressor
from core_engine.obsidian_bridge import ObsidianBridge
from core_engine.governance import PolicyEngine
from core_engine.persona_manager import PersonaManager
from core_engine.bilt_p2p import BiltP2P

if TYPE_CHECKING:
    from core_engine.auto_researcher import AutoResearcher

logger = logging.getLogger(__name__)

# ── Tuning ───────────────────────────────────────────────────────────────────
COMPRESSION_CYCLES       = 4      # fast pass — fewer than full 6-cycle run
PRUNE_THRESHOLD          = 0.10
ACTIVATION_THRESHOLD     = 0.12
MATCH_SCORE_THRESHOLD    = 0.20   # min word-overlap to accept a seed
MAX_CLUSTER_NOTES        = 8
MAX_NOTE_CHARS           = 800
FALLBACK_TOPN            = 3
RESEARCH_GAP_THRESHOLD   = 0.35   # gap urgency score above which auto-research fires
MAX_RESEARCH_HYPOTHESES  = 2      # cap on concurrent research threads per query


class PromptCompressor:
    """
    Full two-way reasoning pipeline between user prompt and the LLM.

    Args:
        vault_path   : path to the Obsidian Vault folder
        obsidian     : ObsidianBridge instance
        researcher   : (optional) AutoResearcher — enables inline empirical gap-filling
    """

    def __init__(
        self,
        vault_path : str,
        obsidian   : ObsidianBridge,
        researcher : "AutoResearcher | None" = None,
    ):
        self.vault_path  = vault_path
        self.compressor  = NeuralCompressor(vault_path, dim=4)
        self.obsidian    = obsidian
        self.researcher  = researcher
        self.governance  = PolicyEngine(vault_path)
        self.persona     = PersonaManager(vault_path)
        self._stop_words = self._build_stop_words()

    # ─────────────────────────────────────────────────────────────────────────
    # PRIMARY ENTRY POINTS
    # ─────────────────────────────────────────────────────────────────────────

    async def compress_query(self, prompt: str) -> dict:
        """
        Full async forward pass.  Returns:
          scaffold         : str        — context block for the LLM
          seeds            : list[str]
          cluster          : list[str]
          gaps             : list[str]
          match_score      : float
          research_results : list[dict] — AutoResearch findings (may be empty)
          trace            : dict       — full audit trail for this pipeline run
          trace_id         : str
        """
        trace_id  = f"TRACE-{uuid.uuid4().hex[:8].upper()}"
        timestamp = datetime.now().isoformat(timespec="seconds")
        trace: dict = {"trace_id": trace_id, "timestamp": timestamp, "prompt": prompt}

        self.governance.load_policies()
        self.persona.load_persona()
        trace["s0_policies"] = [p["id"] for p in self.governance.policies]
        trace["s0_persona"]  = self.persona.persona_name
        
        # Check for iteration
        trace_refs = re.findall(r"TRACE-([A-Z0-9]+)", prompt)
        if trace_refs:
            trace["parent_trace_id"] = f"TRACE-{trace_refs[0]}"
            trace["iteration"] = 2 # Simplified, should ideally look up parent iteration
            logger.info(f"[PromptCompressor:S0] Initializing Iteration Cycle from {trace['parent_trace_id']}")

        logger.info(f"[PromptCompressor:S0] Persona={self.persona.persona_name} Policies={trace['s0_policies']}")

        neurons   = self.compressor.load_neurons()
        all_stems = list(neurons.keys())

        # ── S1: Seed extraction ──────────────────────────────────────────────
        seeds, match_score = self._extract_seeds(prompt, all_stems, neurons)
        if not seeds:
            logger.info("[PromptCompressor] No seed match — hub fallback.")
            seeds = self._hub_fallback(neurons, n=FALLBACK_TOPN)
        trace["s1_seeds"]       = seeds
        trace["s1_match_score"] = round(match_score, 3)
        logger.info(f"[PromptCompressor:S1] Seeds={seeds}  score={match_score:.2f}")

        # ── S2: Hebbian compression ──────────────────────────────────────────
        cluster = self.compressor.run_compression(
            seed_notes           = seeds,
            cycles               = COMPRESSION_CYCLES,
            prune_threshold      = PRUNE_THRESHOLD,
            activation_threshold = ACTIVATION_THRESHOLD,
        )
        trace["s2_cluster"] = cluster
        logger.info(f"[PromptCompressor:S2] Cluster={cluster}")

        # ── S3: Cluster retrieval ────────────────────────────────────────────
        cluster_content: dict[str, str] = {}
        for note in cluster[:MAX_CLUSTER_NOTES]:
            raw = self.obsidian.read_node(note)
            if raw:
                cluster_content[note] = self._strip_frontmatter(raw)[:MAX_NOTE_CHARS]
        trace["s3_retrieved_notes"] = list(cluster_content.keys())

        # ── S4: Gap analysis ─────────────────────────────────────────────────
        gaps = self._find_gaps(prompt, cluster, all_stems)
        trace["s4_gaps"] = gaps
        logger.info(f"[PromptCompressor:S4] Gaps={gaps}")

        # ── S5 + S6: Hypothesis extraction + AutoResearch ───────────────────
        research_results: list[dict] = []
        hypotheses: list[str] = []

        if self.researcher and gaps:
            hypotheses = self._extract_hypotheses(prompt, gaps)
            trace["s5_hypotheses"] = hypotheses

            urgent = [
                h for h in hypotheses
                if self._gap_urgency(h) >= RESEARCH_GAP_THRESHOLD
            ][:MAX_RESEARCH_HYPOTHESES]

            if urgent:
                logger.info(f"[PromptCompressor:S6] AutoResearch firing on: {urgent}")
                research_results = await self._run_research(urgent, trace_id)
                trace["s6_research"] = {
                    "triggered"   : True,
                    "hypotheses"  : urgent,
                    "result_count": len(research_results),
                }
            else:
                trace["s6_research"] = {"triggered": False, "reason": "gap urgency below threshold"}
        else:
            trace["s5_hypotheses"] = []
            trace["s6_research"]   = {
                "triggered": False,
                "reason"   : "no researcher attached" if not self.researcher else "no gaps found",
            }

        # ── S6.5: Human Audit Preparation ────────────────────────────────────
        audit_trail = {
            "status": "PENDING_HUMAN",
            "critical_claims": self._extract_claims(prompt, research_results),
            "logic_path": [seeds, cluster]
        }
        trace["s6_5_audit"] = audit_trail
        logger.info(f"[PromptCompressor:S6.5] Audit trail prepared for HITL verification.")

        # ── S7: Scaffold assembly ────────────────────────────────────────────
        neurons = self.compressor.load_neurons()   # reload after potential Hebbian update
        scaffold = self._build_scaffold(
            prompt           = prompt,
            seeds            = seeds,
            cluster          = cluster,
            cluster_content  = cluster_content,
            gaps             = gaps,
            match_score      = match_score,
            neurons          = neurons,
            research_results = research_results,
            audit_trail      = audit_trail,
            trace_id         = trace_id,
        )
        trace["s7_scaffold_chars"] = len(scaffold)

        return {
            "scaffold"        : scaffold,
            "seeds"           : seeds,
            "cluster"         : cluster,
            "gaps"            : gaps,
            "match_score"     : match_score,
            "research_results": research_results,
            "trace"           : trace,
            "trace_id"        : trace_id,
        }

    def compress_reasoning(self, llm_response: str, original_prompt: str) -> dict:
        """
        Backward pass (S8): compress LLM output back into the vault.
        Runs synchronously (no LLM call needed).

        - Co-mentioned neurons → Hebbian synapse reinforcement
        - Novel concepts       → stub neurons created in neurons.json
        """
        neurons   = self.compressor.load_neurons()
        all_stems = list(neurons.keys())

        response_tokens = self._tokenize(llm_response)
        prompt_tokens   = self._tokenize(original_prompt)

        # Which existing neurons were activated in the response?
        activated = []
        for stem in all_stems:
            stem_tokens = self._tokenize(stem.replace("-", " ").replace("_", " "))
            if stem_tokens and len(stem_tokens & response_tokens) / len(stem_tokens) >= MATCH_SCORE_THRESHOLD:
                activated.append(stem)

        # Hebbian reinforce / create synapses for co-activated pairs
        updated: list[str] = []
        for a in activated:
            for b in activated:
                if a == b:
                    continue
                data_a = neurons[a]
                if b in data_a["synapses"]:
                    vec = data_a["synapses"][b]
                    for i in range(self.compressor.dim):
                        vec[i] = vec[i] * 0.90 + 0.10
                else:
                    data_a["synapses"][b] = self.compressor._init_vector(a, b)
                updated.append(a)

        # Novel concept stubs
        all_tokens = set()
        for stem in all_stems:
            all_tokens |= self._tokenize(stem.replace("-", " ").replace("_", " "))

        novel = [
            t for t in (response_tokens - prompt_tokens - all_tokens - self._stop_words)
            if len(t) > 5
        ][:5]

        new_neurons: list[str] = []
        for token in novel:
            stub_id = f"CONCEPT-{token.upper()}"
            if stub_id not in neurons:
                neurons[stub_id] = {"activation": 0.0, "synapses": {}, "fixed": False, "stub": True}
                new_neurons.append(stub_id)

        self.compressor.save_neurons(neurons)
        logger.info(
            f"[PromptCompressor:S8] {len(set(updated))} synapses reinforced, "
            f"{len(new_neurons)} stub neurons created."
        )

        return {"updated_neurons": list(set(updated)), "new_neurons": new_neurons}

    def reinforce_cluster(self, cluster: list[str], score: float) -> None:
        """
        Reward-based Synaptic Reinforcement.
        Increases magnitude of synapses between nodes in the cluster 
        if the reasoning was grounded (high score).
        """
        if score < 0.5:
            # Low score = potential penalty (depression)
            penalty = 0.95
            logger.info(f"[PromptCompressor] Low grounding score ({score:.2f}). Applying synaptic depression.")
        else:
            # High score = boost
            penalty = 1.0 + (score * 0.05) # Max 5% boost per pass
            logger.info(f"[PromptCompressor] High grounding score ({score:.2f}). Applying synaptic boost.")

        neurons = self.compressor.load_neurons()
        for a in cluster:
            if a not in neurons: continue
            for b in cluster:
                if a == b or b not in neurons[a]["synapses"]: continue
                vec = neurons[a]["synapses"][b]
                for i in range(self.compressor.dim):
                    vec[i] = min(1.0, vec[i] * penalty)
        
        self.compressor.save_neurons(neurons)

    async def persist_trace(self, trace: dict, llm_response: str, validation_score: float = 0.0) -> str:
        """
        S9: Write a full audit trail to the Vault as a readable Obsidian note.
        Returns the trace node ID.
        """
        trace_id = trace.get("trace_id", f"TRACE-{uuid.uuid4().hex[:8].upper()}")
        parent_id = trace.get("parent_trace_id")
        iteration = trace.get("iteration", 1)
        
        content  = f"# Reasoning Trace {trace_id} (Iteration {iteration})\n\n"
        if parent_id:
            content += f"**Parent Trace:** [[{parent_id}]]\n"
        content += f"**Timestamp:** {trace.get('timestamp', 'unknown')}\n"
        content += f"**Original Query:** {trace.get('prompt', '')}\n\n"

        content += "## S1 — Seed Extraction\n"
        content += f"- Seeds: `{trace.get('s1_seeds', [])}`\n"
        content += f"- Match confidence: `{trace.get('s1_match_score', 0):.0%}`\n\n"

        content += "## S2 — Hebbian Compression\n"
        content += f"- Cluster: `{trace.get('s2_cluster', [])}`\n\n"

        content += "## S3 — Retrieved Notes\n"
        for n in trace.get("s3_retrieved_notes", []):
            content += f"- [[{n}]]\n"
        content += "\n"

        content += "## S4 — Knowledge Gaps\n"
        for g in trace.get("s4_gaps", []):
            content += f"- `{g}`\n"
        content += "\n"

        content += "## S5 — Hypotheses Extracted\n"
        for h in trace.get("s5_hypotheses", []):
            content += f"- {h}\n"
        content += "\n"

        research = trace.get("s6_research", {})
        content += "## S6 — AutoResearch\n"
        content += f"- Triggered: `{research.get('triggered', False)}`\n"
        if research.get("triggered"):
            content += f"- Hypotheses run: `{research.get('hypotheses', [])}`\n"
            content += f"- Results produced: `{research.get('result_count', 0)}`\n"
        else:
            content += f"- Reason skipped: {research.get('reason', 'unknown')}\n"
        content += "\n"

        content += "## S7 — Scaffold\n"
        content += f"- Scaffold size: `{trace.get('s7_scaffold_chars', 0)} chars`\n\n"

        content += "## LLM Response\n"
        content += f"```\n{llm_response[:1200] if llm_response else 'No response'}\n```\n\n"

        content += f"## Validation Score\n- `{validation_score:.2f}`\n"

        self.obsidian.write_node(
            node_id    = trace_id,
            tags       = ["trace/reasoning", "empirical/verified" if validation_score > 0.7 else "hypothesis/unconfirmed"],
            parent_nodes = trace.get("s1_seeds", []),
            content    = content,
            node_type  = "reasoning_trace",
        )

        logger.info(f"[PromptCompressor:S9] Trace persisted → {trace_id}.md")
        return trace_id

    # ─────────────────────────────────────────────────────────────────────────
    # INTERNAL — SCAFFOLD BUILDER
    # ─────────────────────────────────────────────────────────────────────────

    def _build_scaffold(
        self,
        prompt          : str,
        seeds           : list,
        cluster         : list,
        cluster_content : dict,
        gaps            : list,
        match_score     : float,
        neurons         : dict,
        research_results: list,
        p2p_results     : list,
        trace_id        : str,
    ) -> str:
        lines: list[str] = []

        # ── Header ──────────────────────────────────────────────────────────
        lines += [
            "=== VAULT CONTEXT — Verified Reasoning Pipeline ===",
            f"Trace: {trace_id} | Confidence: {match_score:.0%} | Audit: PENDING_HUMAN",
            "",
        ]

        # ── SYSTEM IDENTITY ──────────────────────────────────────────────────
        lines.append(self.persona.get_persona_scaffold())
        lines.append("")

        # ── POLICIES ─────────────────────────────────────────────────────────
        lines.append(self.governance.get_active_policies_text())
        lines.append("")

        # ── KNOWN ────────────────────────────────────────────────────────────
        if cluster_content:
            lines.append("[KNOWN — Vault-grounded facts | treat as authoritative]")
            for note, content in cluster_content.items():
                is_guidance = "GUIDANCE" in note.upper() or "THEORY" in note.upper()
                prefix = "  [AXIOM] " if is_guidance else "  Note: "
                lines.append(f"\n{prefix}{note}")
                for ln in content.strip().splitlines()[:12]:
                    if ln.strip():
                        lines.append(f"  | {ln.strip()}")
            lines.append("")
        else:
            lines += ["[KNOWN — No vault facts matched this query]", ""]

        # ── RESEARCHED ───────────────────────────────────────────────────────
        if research_results:
            lines.append("[RESEARCHED — Empirically verified findings from AutoResearch]")
            for r in research_results:
                lines.append(f"\n  Hypothesis: {r.get('hypothesis', '?')}")
                lines.append(f"  Status:     {r.get('status', 'unknown')}")
                findings = r.get("findings", "")
                if findings:
                    for fl in str(findings).splitlines()[:6]:
                        if fl.strip():
                            lines.append(f"  > {fl.strip()}")
            lines.append("")
        else:
            lines += ["[RESEARCHED — No empirical research conducted for this query]", ""]

        # ── HUMAN AUDIT BLOCK ────────────────────────────────────────────────
        lines.append("[HUMAN AUDIT BLOCK — Verification trail for Admin/Instructor]")
        lines.append(f"  Status: {audit_trail.get('status')}")
        lines.append("  Claims to Verify:")
        for claim in audit_trail.get("critical_claims", []):
            lines.append(f"    - {claim}")
        lines.append("  Logic Manifest:")
        lines.append(f"    Seeds: {audit_trail.get('logic_path')[0]}")
        lines.append(f"    Cluster: {audit_trail.get('logic_path')[1]}")
        lines.append("")

        # ── CONNECTIONS ──────────────────────────────────────────────────────
        lines.append("[CONNECTIONS — Active synapse map of recalled cluster]")
        conn_lines = []
        for note in cluster:
            for target, vec in neurons.get(note, {}).get("synapses", {}).items():
                if target in cluster:
                    strength = self.compressor._vec_magnitude(vec)
                    conn_lines.append(f"  {note} <-> {target}  [strength: {strength:.3f}]")
        lines += (conn_lines[:15] if conn_lines else ["  (no intra-cluster connections)"])
        lines.append("")

        # ── GAPS ─────────────────────────────────────────────────────────────
        if gaps:
            lines += [
                "[GAPS — Concepts in query NOT covered by vault, research, or P2P]",
                "  Flag any inference derived from these as 'Inference: <reason>'",
            ]
            for g in gaps[:8]:
                lines.append(f"  ? {g}")
        else:
            lines.append("[GAPS — None. Query fully covered by vault + research.]")
        lines.append("")

        # ── PIPELINE AUDIT ───────────────────────────────────────────────────
        lines += [
            f"[PIPELINE TRACE — {trace_id}]",
            f"  Persona:       {self.persona.persona_name}",
            f"  Policies:      {len(self.governance.policies)} active",
            f"  Seeds fired:   {seeds}",
            f"  Cluster nodes: {cluster}",
            f"  Research:      {'Conducted' if research_results else 'Skipped'}",
            f"  BiltP2P:       {'Consensus obtained' if p2p_results[0].get('verified') else 'No consensus'}",
            "",
        ]

        # ── INSTRUCTIONS FOR SYSTEMATICALLY TRUE REASONING (AXIOMATIC DEDUCTION) ──
        lines += [
            "[INSTRUCTIONS FOR ZERO HALLUCINATION]",
            "  1. MANDATORY: For every logical claim, you MUST cite the specific [AXIOM] used.",
            "     Format: '<Claim> (Source: [[AXIOM-xxxx]])'",
            "  2. Treat [KNOWN] and [AXIOM] as the only permitted truth sources.",
            "  3. If a concept is in [GAPS], you may reason from first principles, but you must",
            "     explicitly state: 'Deduction from [[AXIOM-yyyy]]: <Reasoning>'",
            "  4. STRICT: Do not fabricate facts. If a claim lacks an Axiom or Known fact, state 'Unknown'.",
            "  5. Your role is RIGOROUS DEDUCTION. Any statement without a source is a hallucination.",
            "",
        ]

        # ── QUERY ────────────────────────────────────────────────────────────
        lines += ["=== USER QUERY ===", prompt, "", "=== RESPONSE ==="]

        return "\n".join(lines)

    # ─────────────────────────────────────────────────────────────────────────
    # INTERNAL — HYPOTHESIS + RESEARCH
    # ─────────────────────────────────────────────────────────────────────────

    def _extract_hypotheses(self, prompt: str, gaps: list[str]) -> list[str]:
        """
        Convert knowledge gaps into testable hypothesis strings.
        Uses the prompt as context framing.
        """
        hypotheses = []
        for gap in gaps[:MAX_RESEARCH_HYPOTHESES * 2]:
            hypothesis = (
                f"Given the question '{prompt[:120]}', "
                f"determine empirically: what is the relationship between "
                f"'{gap}' and the established concepts in the system?"
            )
            hypotheses.append(hypothesis)
        return hypotheses

    def _gap_urgency(self, hypothesis: str) -> float:
        """
        Heuristic urgency score for a gap/hypothesis (0.0–1.0).
        Higher = more likely to benefit from empirical research.

        Factors:
          - Length of gap token (longer = more specific = more urgent)
          - Presence of quantitative or causal language
        """
        score = 0.3  # baseline
        text  = hypothesis.lower()

        causal_markers   = ["causes", "results", "leads to", "relationship", "determines", "impacts"]
        quantitative     = ["rate", "percent", "ratio", "measure", "calculate", "compute", "number"]
        mechanism_words  = ["mechanism", "process", "algorithm", "how", "why", "proof", "derive"]

        for m in causal_markers:
            if m in text: score += 0.10
        for q in quantitative:
            if q in text: score += 0.08
        for w in mechanism_words:
            if w in text: score += 0.07

        return min(score, 1.0)

    async def _run_research(self, hypotheses: list[str], parent_trace_id: str) -> list[dict]:
        """
        Fire AutoResearcher on each hypothesis concurrently.
        Results are returned as structured dicts for scaffold injection.
        """
        if not self.researcher:
            return []

        results = []
        tasks   = []

        for hyp in hypotheses:
            node_id = f"RES-{uuid.uuid4().hex[:6].upper()}"
            task    = asyncio.create_task(
                self.researcher.execute_empirical_verification(hyp, node_id)
            )
            tasks.append((hyp, node_id, task))

        for hyp, node_id, task in tasks:
            try:
                await asyncio.wait_for(task, timeout=60.0)   # 60s max per research task
                # Read back the evidence node written by AutoResearcher to Obsidian
                evidence = self.obsidian.read_node(node_id)
                results.append({
                    "hypothesis": hyp,
                    "status"    : "completed",
                    "node_id"   : node_id,
                    "findings"  : self._strip_frontmatter(evidence) if evidence else "No output",
                })
            except asyncio.TimeoutError:
                results.append({"hypothesis": hyp, "status": "timeout", "node_id": node_id, "findings": ""})
            except Exception as e:
                results.append({"hypothesis": hyp, "status": f"error: {e}", "node_id": node_id, "findings": ""})

        return results

    # ─────────────────────────────────────────────────────────────────────────
    # INTERNAL — SEED EXTRACTION
    # ─────────────────────────────────────────────────────────────────────────

    def _extract_seeds(self, prompt: str, all_stems: list, neurons: dict = None) -> tuple[list, float]:
        prompt_tokens = self._tokenize(prompt)
        scored        = []

        for stem in all_stems:
            stem_clean  = stem.replace("-", " ").replace("_", " ")
            stem_tokens = self._tokenize(stem_clean)
            if not stem_tokens:
                continue

            overlap_ratio = len(stem_tokens & prompt_tokens) / len(stem_tokens)

            if stem_clean.lower() in prompt.lower():
                overlap_ratio = max(overlap_ratio, 0.9)

            for lt in [t for t in stem_tokens if len(t) >= 5]:
                if lt in prompt_tokens:
                    overlap_ratio += 0.15

        # Detect explicit TRACE references
        trace_refs = re.findall(r"TRACE-[A-Z0-9]+", prompt)
        if neurons:
            for t in trace_refs:
                if t in neurons:
                    scored.append((t, 1.0))
                    logger.info(f"[PromptCompressor] Explicit TRACE reference detected: {t}")

        scored.sort(key=lambda x: x[1], reverse=True)
        seeds     = [s[0] for s in list(dict.fromkeys([s[0] for s in scored]))][:6]
        max_score = scored[0][1] if scored else 0.0
        return seeds, max_score

    def _hub_fallback(self, neurons: dict, n: int = FALLBACK_TOPN) -> list:
        # Prioritize Fixed/Guidance neurons in fallback
        fixed = [k for k, v in neurons.items() if v.get("fixed")]
        if fixed:
            return fixed[:n]
            
        return sorted(
            neurons.keys(),
            key=lambda k: len(neurons[k].get("synapses", {})),
            reverse=True
        )[:n]

    # ─────────────────────────────────────────────────────────────────────────
    # INTERNAL — GAP ANALYSIS
    # ─────────────────────────────────────────────────────────────────────────

    def _find_gaps(self, prompt: str, cluster: list, all_stems: list) -> list:
        prompt_tokens  = self._tokenize(prompt) - self._stop_words
        cluster_tokens : set = set()
        for stem in cluster:
            cluster_tokens |= self._tokenize(stem.replace("-", " ").replace("_", " "))

        return sorted([
            t for t in (prompt_tokens - cluster_tokens)
            if len(t) >= 4 and not t.isdigit()
        ])[:10]

    def _extract_claims(self, prompt: str, research: list) -> list:
        """Simple heuristic to extract truth-claims for human audit."""
        claims = [f"Direct prompt intent: {prompt[:100]}..."]
        for r in research:
            claims.append(f"Empirical claim: {r.get('hypothesis')[:100]}...")
        return claims

    # ─────────────────────────────────────────────────────────────────────────
    # UTILITIES
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _tokenize(text: str) -> set:
        return {t for t in re.split(r'[^a-z0-9]+', text.lower()) if t}

    @staticmethod
    def _strip_frontmatter(text: str) -> str:
        if text.startswith("---"):
            end = text.find("---", 3)
            if end != -1:
                return text[end + 3:].strip()
        return text.strip()

    @staticmethod
    def _build_stop_words() -> set:
        return {
            "the","a","an","and","or","but","in","on","at","to","for",
            "of","with","by","from","up","about","into","through","is",
            "are","was","were","be","been","being","have","has","had",
            "do","does","did","will","would","could","should","may","might",
            "this","that","these","those","it","its","they","we","you","i",
            "what","which","who","when","where","why","how","not","no","so",
            "just","also","as","if","can","than","then","said","use",
        }
