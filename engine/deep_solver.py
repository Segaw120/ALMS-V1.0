import asyncio
import logging
import uuid
import re
from typing import List, Dict

from core_engine.llm_manager import LLMManager
from core_engine.obsidian_bridge import ObsidianBridge
from core_engine.memory_manager import MemoryManager
from core_engine.logic_validator import LogicValidator
from core_engine.auto_researcher import AutoResearcher

class DeepSolver:
    """
    Continuous problem-solving engine.
    Maintains a persistent state of inquiry and recursively triggers 
    AutoResearch until a complex question is 'solved' or a threshold is reached.
    """
    def __init__(self, llm: LLMManager, obsidian: ObsidianBridge, memory: MemoryManager, validator: LogicValidator, researcher: AutoResearcher):
        self.llm = llm
        self.obsidian = obsidian
        self.memory = memory
        self.validator = validator
        self.researcher = researcher
        self.active_tasks = {}

    async def solve_continuously(self, query: str, task_id: str | None = None, status_callback = None):
        """
        Starts a continuous background solving loop for a user query.
        """
        if not task_id:
            task_id = f"SOLVE-{uuid.uuid4().hex[:6].upper()}"
        
        self.active_tasks[task_id] = {"query": query, "status": "active", "iterations": 0}
        logging.info(f"[DeepSolver] Starting continuous solve for task: {task_id} | Query: {query}")
        
        if status_callback:
            await status_callback(f"Initializing Deep Solve for: {query}")

        # Initialize State in Obsidian
        self.obsidian.write_node(
            node_id=task_id,
            tags=["solver/active", "goal/deep_solve"],
            parent_nodes=[],
            content=f"# Deep Solve Objective\n{query}\n\n## Current Status\nInitializing continuous reasoning loop...",
            node_type="solve_state"
        )

        try:
            # Main Solving Loop (Max 5 iterations for now to prevent runaway)
            for i in range(5):
                if task_id not in self.active_tasks or self.active_tasks[task_id]["status"] == "cancelled":
                    break
                
                self.active_tasks[task_id]["iterations"] += 1
                logging.info(f"[DeepSolver] Iteration {i+1} for {task_id}")
                if status_callback:
                    await status_callback(f"Iteration {i+1}: Analyzing knowledge gaps...")

                # 1. Gap Analysis: What is missing?
                gaps = await self._analyze_knowledge_gaps(task_id, query)
                if not gaps or "solved" in gaps.lower():
                    logging.info(f"[DeepSolver] Task {task_id} determined to be SOLVED.")
                    if status_callback:
                        await status_callback("Solution verified! Finalizing...")
                    break

                # 2. Hypothesis Generation: How do we fill the gaps?
                if status_callback:
                    await status_callback(f"Gaps identified. Generating testable hypotheses...")
                hypotheses = await self._generate_testable_hypotheses(query, gaps)
                
                # 3. Autonomous Execution: Trigger AutoResearcher
                research_tasks = []
                for hypo in hypotheses[:2]: # Max 2 concurrent research tasks per iteration
                    if status_callback:
                        await status_callback(f"Triggering Auto-Research: {hypo}")
                    research_tasks.append(
                        self.researcher.execute_empirical_verification(
                            hypothesis=hypo,
                            target_node_id=task_id,
                            parent_trace_id=task_id
                        )
                    )
                
                if research_tasks:
                    logging.info(f"[DeepSolver] Triggering {len(research_tasks)} research tasks for {task_id}")
                    await asyncio.gather(*research_tasks)

                # 4. State Update: Consolidate new findings
                if status_callback:
                    await status_callback(f"Consolidating findings and updating state...")
                await self._consolidate_findings(task_id)

                # Wait before next iteration to simulate "deep thought" and avoid rate limits
                await asyncio.sleep(2)

            # Final Summary
            await self._finalize_solution(task_id)

        except Exception as e:
            logging.error(f"[DeepSolver] Error in task {task_id}: {str(e)}")
            self.active_tasks[task_id]["status"] = "error"
        finally:
            if task_id in self.active_tasks:
                self.active_tasks[task_id]["status"] = "complete"

    async def _analyze_knowledge_gaps(self, task_id: str, query: str) -> str:
        """Determines what information is still missing to fully answer the query."""
        # Fetch current state from Obsidian
        state_content = self.obsidian.read_node(task_id)
        
        prompt = (
            "You are the Meta-Analyst. Your goal is to solve the user's objective.\n"
            f"Objective: {query}\n"
            f"Current Knowledge State:\n{state_content}\n\n"
            "Identify exactly what information is still missing, contradictory, or unverified.\n"
            "If the objective is fully solved with empirical evidence, reply with the word 'SOLVED'.\n"
            "Otherwise, list the specific knowledge voids."
        )
        return await self.llm.generate_response(prompt)

    async def _generate_testable_hypotheses(self, query: str, gaps: str) -> List[str]:
        """Generates hypotheses that can be tested by the AutoResearcher."""
        prompt = (
            "You are the Lead Researcher. Given the objective and the identified knowledge gaps, "
            "propose 1-3 specific, testable hypotheses that can be verified via Python code (math, data simulation, or API scraping).\n"
            f"Objective: {query}\n"
            f"Gaps: {gaps}\n\n"
            "Format: One hypothesis per line. Be extremely specific and technical."
        )
        response = await self.llm.generate_response(prompt)
        return [h.strip() for h in response.split('\n') if h.strip() and len(h) > 10]

    async def _consolidate_findings(self, task_id: str):
        """Updates the main solve node with summarized results of all sub-experiments."""
        # Find all EXP nodes linked to this solve task
        nodes = os.listdir(self.obsidian.vault_path)
        exp_nodes = [f.replace(".md", "") for f in nodes if f.startswith("EXP-")]
        
        findings = []
        for node_id in exp_nodes:
            content = self.obsidian.read_node(node_id)
            if f"[[{task_id}]]" in content:
                # Extract summary
                match = re.search(r'# Empirical Results\n```text\n(.*?)\n```', content, re.DOTALL)
                if match:
                    findings.append(f"- **{node_id}**: {match.group(1)[:200]}...")

        if findings:
            current_state = self.obsidian.read_node(task_id)
            updated_content = current_state + f"\n\n### Findings from Iteration\n" + "\n".join(findings)
            self.obsidian.write_node(
                node_id=task_id,
                tags=["solver/active"],
                parent_nodes=[],
                content=updated_content,
                node_type="solve_state",
                overwrite=True
            )

    async def _finalize_solution(self, task_id: str):
        """Generates a final, high-nuance synthesis of the entire solving process."""
        state_content = self.obsidian.read_node(task_id)
        prompt = (
            "You are the Superman Synthesizer. You have completed a continuous solving loop.\n"
            "Based on all the empirical evidence collected, provide the definitive answer to the objective.\n"
            "Structure: Executive Summary, Verified Axioms, and Final Tactical Recommendation.\n"
            f"Knowledge State:\n{state_content}"
        )
        final_answer = await self.llm.generate_response(prompt)
        
        content = f"# FINAL SOLUTION: {task_id}\n\n{final_answer}\n\n---\n## Process History\n{state_content}"
        self.obsidian.write_node(
            node_id=task_id,
            tags=["solver/complete", "logic/verified"],
            parent_nodes=[],
            content=content,
            node_type="solve_state",
            overwrite=True
        )
        logging.info(f"[DeepSolver] Finalized {task_id}")
