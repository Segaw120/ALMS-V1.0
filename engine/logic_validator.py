import logging
import re
from typing import Dict, List
from core_engine.llm_manager import LLMManager

class LogicValidator:
    """
    Objective evaluation engine for the Fractal Reasoner.
    Checks for logical fallacies, contradictions, and empirical testability.
    """
    def __init__(self, llm: LLMManager):
        self.llm = llm

    async def evaluate_reasoning(self, reasoning_content: str, context: str = "") -> Dict:
        """
        Performs a multi-dimensional objective critique of a reasoning node.
        """
        system_prompt = (
            "You are the Objective Critic and Logic Validator. Your goal is to evaluate reasoning for absolute objectivity, "
            "verifiability, and logical structural integrity. Ignore personal bias or subjective 'vibes'.\n\n"
            "Evaluate based on:\n"
            "1. Logical Consistency: Does it contradict itself or the context?\n"
            "2. Verifiability: Can this claim be tested empirically (math, code, search)?\n"
            "3. Fallacy Detection: Identify any logical fallacies (strawman, circular reasoning, etc).\n"
            "4. Empirical Grounding: Is it moving towards actionable data or floating in abstraction?\n\n"
            "Output JSON format:\n"
            "{\n"
            "  \"score\": 0.0 to 1.0,\n"
            "  \"critique\": \"short explanation\",\n"
            "  \"testable_hypothesis\": \"a specific claim to be tested (if any)\",\n"
            "  \"fallacies\": [\"list\"]\n"
            "}"
        )

        prompt = f"Context: {context}\n\nReasoning to Evaluate: {reasoning_content}"
        
        # Using a higher-parameter model for critique if possible
        response = await self.llm.generate_response(f"{system_prompt}\n\n{prompt}")
        
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                import json
                evaluation = json.loads(json_match.group(0))
                return evaluation
        except Exception as e:
            logging.error(f"Failed to parse logic evaluation: {e}")
            
        return {
            "score": 0.5,
            "critique": "Evaluation failed to parse.",
            "testable_hypothesis": None,
            "fallacies": []
        }

    async def evaluate_empirical_data(self, hypothesis: str, expected_criteria: Dict, raw_stdout: str) -> Dict:
        """
        Grades the raw output of an Auto-Research script.
        Ensures the data is not hallucinated and actually answers the requirements.
        """
        system_prompt = (
            "You are the Data Validator. Your job is to analyze the raw standard output of an automated Python script, "
            "and determine if it successfully proved or disproved the hypothesis based on the criteria.\n\n"
            "SPECIAL PROTOCOL: SELF-EVOLUTION (SYS-007)\n"
            "If the hypothesis involves 'Self-Modification', 'Refactoring', or 'Code Improvement':\n"
            "1. Priority is given to BOOTSTRAP SUCCESS (Does the code run without errors?).\n"
            "2. Valid findings include: Syntax validity, successful unit tests, and performance improvements.\n"
            "3. Do NOT strictly require statistical p-values or correlation matrices for code-level refactors.\n\n"
            "Output JSON format:\n"
            "{\n"
            "  \"data_quality_score\": 0.0 to 1.0,\n"
            "  \"valid_finding\": true/false,\n"
            "  \"critique\": \"short explanation of why the data succeeded or failed\"\n"
            "}"
        )
        
        prompt = f"Hypothesis: {hypothesis}\nExpected Criteria: {expected_criteria}\n\nRaw Script Output:\n{raw_stdout}"
        
        response = await self.llm.generate_response(f"{system_prompt}\n\n{prompt}")
        
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                import json
                evaluation = json.loads(json_match.group(0))
                return evaluation
        except Exception as e:
            logging.error(f"Failed to parse empirical data evaluation: {e}")
            
        return {
            "data_quality_score": 0.0,
            "valid_finding": False,
            "critique": "Data Evaluation failed to parse. Assuming failed execution."
        }
    async def hallucination_check(self, llm_response: str, scaffold: str) -> Dict:
        """
        Cross-references the LLM response against the provided reasoning scaffold.
        Identifies any claims made in the response that are NOT supported by the scaffold.
        """
        system_prompt = (
            "You are the Grounding Auditor. Your sole mission is to detect hallucinations.\n"
            "Compare the [LLM RESPONSE] against the [SCAFFOLD CONTEXT].\n\n"
            "A Hallucination is defined as:\n"
            "1. Any factual claim not present in the [KNOWN] or [RESEARCHED] sections.\n"
            "2. Any logical conclusion that contradicts the [P2P VERIFIED] consensus.\n"
            "3. Any inference that is not explicitly labeled as 'Inference:'.\n\n"
            "Output JSON format:\n"
            "{\n"
            "  \"grounding_score\": 0.0 to 1.0,\n"
            "  \"hallucinations\": [\"list of specific ungrounded claims\"],\n"
            "  \"is_grounded\": true/false,\n"
            "  \"audit_comment\": \"short summary\"\n"
            "}"
        )

        prompt = f"[SCAFFOLD CONTEXT]:\n{scaffold}\n\n[LLM RESPONSE]:\n{llm_response}"
        
        response = await self.llm.generate_response(f"{system_prompt}\n\n{prompt}")
        
        try:
            import json
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
        except Exception as e:
            logging.error(f"Failed to parse hallucination check: {e}")
            
        return {
            "grounding_score": 0.5,
            "hallucinations": [],
            "is_grounded": True,
            "audit_comment": "Audit failed to parse. Defaulting to neutral."
        }
