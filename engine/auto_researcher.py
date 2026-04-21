import os
import uuid
import re
import asyncio
import subprocess
import tempfile
import logging

from core_engine.llm_manager import LLMManager
from core_engine.obsidian_bridge import ObsidianBridge
from core_engine.logic_validator import LogicValidator

class AutoResearcher:
    """
    Empirical execution engine. Receives theoretical hypotheses from the 
    Fractal Reasoner, writes Python scripts to test them, executes them 
    in a sandboxed subprocess, natively refactors on error, and pipes 
    the result back to Obsidian as empirical evidence.
    """
    def __init__(self, llm: LLMManager, obsidian: ObsidianBridge, validator: LogicValidator):
        self.llm = llm
        self.obsidian = obsidian
        self.validator = validator

    async def execute_empirical_verification(
        self,
        hypothesis     : str,
        target_node_id : str,
        parent_trace_id: str | None = None,   # links experiment to its spawning TRACE node
    ):
        """Main orchestrated loop for empirical verification."""
        logging.info(f"[AutoResearcher] Initiating empirical verification for [{target_node_id}]")
        logging.info(f"[AutoResearcher] Parent trace: {parent_trace_id or 'none'}")

        # 1. Define success criteria
        criteria = await self._define_success_criteria(hypothesis)
        if not criteria:
            logging.error("[AutoResearcher] Failed to generate test-driven criteria.")
            return
            
        logging.info(f"Generated Criteria: {criteria}")

        # 2. Double-Blind Execution Loop
        methodologies = ["statistical approximation/simulation", "direct API data scraping or math formulas"]
        validation_results = []
        
        for idx, method in enumerate(methodologies):
            logging.info(f"Starting Double-Blind pass {idx+1}/{len(methodologies)} using: {method}")
            # Generate code using specific method
            script_code = await self._generate_experiment_script(hypothesis, criteria, method)
            if not script_code: continue

            # Execute & Refactor (Max 3 retries)
            execution_output, run_success = await self._sandbox_execute(script_code)
            
            if run_success:
                # Post-Execution Result Validation via LogicValidator
                eval_result = await self.validator.evaluate_empirical_data(hypothesis, criteria, execution_output)
                
                if eval_result.get("valid_finding") is True and eval_result.get("data_quality_score", 0.0) >= 0.7:
                    logging.info(f"Pass {idx+1} mathematically validated! Score: {eval_result['data_quality_score']}")
                    validation_results.append((execution_output, eval_result['critique']))
                else:
                    logging.warning(f"Pass {idx+1} executed, but DATA failed logic validation. Critique: {eval_result.get('critique')}")
            else:
                logging.warning(f"Pass {idx+1} failed to execute properly.")
                
        # 3. Format and deliver to Obsidian
        if len(validation_results) == 2:
            final_output = f"# Pass 1 Results\n{validation_results[0][0]}\n\n# Pass 2 Results\n{validation_results[1][0]}"
            self._save_evidence_node(target_node_id, final_output, True, True, parent_trace_id)
        elif len(validation_results) == 1:
            final_output = f"Single Pass Succeeded.\n{validation_results[0][0]}"
            self._save_evidence_node(target_node_id, final_output, True, False, parent_trace_id)
        else:
            self._save_evidence_node(
                target_node_id,
                "Failed continuous autonomous retries or logic validation.",
                False, False, parent_trace_id
            )

    async def _define_success_criteria(self, hypothesis: str) -> dict:
        """Test-Driven Research: Determines what a valid finding must look like."""
        prompt = (
            "You are the Research Architect. Given a hypothesis, define strict criteria for empirical testing. "
            "Output JSON format:\n"
            "{\n"
            "  \"core_metric\": \"What specific number or data structure must be printed?\",\n"
            "  \"assertion\": \"What evaluates to True if the hypothesis is correct?\"\n"
            "}"
        )
        response = await self.llm.generate_response(f"{prompt}\n\nHypothesis: {hypothesis}")
        try:
            import json
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
        except Exception:
            pass
        return {"core_metric": "stdout prints success data", "assertion": "results are logically sound"}

    async def _generate_experiment_script(self, hypothesis: str, criteria: dict, methodology: str) -> str:
        prompt = (
            "You are the Auto-Researcher Coding Agent. You must write a self-contained Python script to test the following hypothesis empirically.\n"
            f"Methodology to employ: {methodology}\n"
            f"Hypothesis: {hypothesis}\n"
            f"Required Output Metric: {criteria['core_metric']}\n"
            "Requirement: Output ONLY valid, executable Python code inside a markdown block (```python ... ```). Focus on achieving the core metric and printing the exact result."
        )
        # Routes through LLMManager default (gemma4:31b-cloud)
        response = await self.llm.generate_response(prompt)
        
        if not response:
            return ""
            
        # Extract the exact code block
        match = re.search(r'```python\n(.*?)\n```', response, re.DOTALL)
        if match:
            return match.group(1)
        return ""

    async def _sandbox_execute(self, code: str, retries: int = 3):
        """
        Runs the code in a mocked sandbox via python subprocess.
        Loops to autonomously fix tracebacks via LLM reasoning.
        """
        current_code = code
        for attempt in range(retries):
            # Write temp file
            with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode='w', encoding='utf-8') as temp_file:
                temp_file.write(current_code)
                temp_path = temp_file.name

            env = os.environ.copy()
            env["MPLBACKEND"] = "Agg"
            try:
                import time
                start_time = time.time()
                
                # Execute in subprocess
                result = subprocess.run(
                    ["python", temp_path],
                    capture_output=True,
                    text=True,
                    timeout=30, # 30s max empirical runtime to prevent hang
                    env=env
                )
                
                latency = time.time() - start_time
                
                # Report latency to Supabase
                from core_engine.reporter import reporter
                asyncio.create_task(reporter.log_event("RESEARCH_PERFORMANCE", {
                    "latency_seconds": round(latency, 3),
                    "attempt": attempt + 1,
                    "return_code": result.returncode
                }))
                
                os.remove(temp_path)
                
                # Check for success
                if result.returncode == 0:
                    return result.stdout.strip(), True
                else:
                    # Error caught - Autonomous Refactor
                    error_trace = result.stderr.strip()
                    logging.warning(f"Execution Error on Attempt {attempt+1}. Requesting autonomous refactor...")
                    
                    refactor_prompt = (
                        f"The following python script crashed:\n```python\n{current_code}\n```\n\n"
                        f"Error Traceback:\n{error_trace}\n\n"
                        f"Refactor and fix this code. Output ONLY the fixed python code inside a markdown block."
                    )
                    fix_response = await self.llm.generate_response(refactor_prompt)
                    if fix_response:
                        match = re.search(r'```python\n(.*?)\n```', fix_response, re.DOTALL)
                        if match:
                            current_code = match.group(1)
                    
            except subprocess.TimeoutExpired:
                os.remove(temp_path)
                return "Execution Timeout. Script exceeded empirical runtime constraints.", False

        return "Max autonomous refactoring attempts exhausted.", False

    def _save_evidence_node(
        self,
        target_node     : str,
        results         : str,
        success         : bool,
        double_blind    : bool,
        parent_trace_id : str | None = None,
    ):
        """Formats and writes the empirical evidence to Obsidian with full trace backlinks."""
        evidence_id = f"EXP-{uuid.uuid4().hex[:6].upper()}"

        if success and double_blind:
            status_tag = "truth/axiom"
        elif success:
            status_tag = "empirical/single_pass"
        else:
            status_tag = "empirical/failed"

        # Build backlink block
        backlinks = f"\n\n---\n## Trace Backlinks\n"
        backlinks += f"- Hypothesis target: [[{target_node}]]\n"
        if parent_trace_id:
            backlinks += f"- Spawned by trace: [[{parent_trace_id}]]\n"

        metadata_block = (
            f"**Experiment ID:** {evidence_id}\n"
            f"**Hypothesis target:** [[{target_node}]]\n"
        )
        if parent_trace_id:
            metadata_block += f"**Parent trace:** [[{parent_trace_id}]]\n"
        metadata_block += (
            f"**Status:** {'AXIOM (double-blind confirmed)' if double_blind else 'single pass' if success else 'FAILED'}\n\n"
        )

        content = (
            metadata_block
            + f"# Empirical Results\n```text\n{results}\n```\n\n"
            + f"# Axiom Verified\n{success}\n"
            + f"# Double-Blind Confirmed\n{double_blind}\n"
            + backlinks
        )

        tags = [f"target/{target_node}", status_tag]
        if parent_trace_id:
            tags.append(f"trace/{parent_trace_id}")

        parent_nodes = [target_node]
        if parent_trace_id:
            parent_nodes.append(parent_trace_id)

        self.obsidian.write_node(
            node_id      = evidence_id,
            tags         = tags,
            parent_nodes = parent_nodes,
            content      = content,
            node_type    = "empirical_evidence",
        )
        logging.info(f"[AutoResearcher] Evidence {evidence_id} linked to {target_node} | trace={parent_trace_id}")
        return evidence_id

