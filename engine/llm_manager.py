import logging
from typing import TYPE_CHECKING
from ollama import AsyncClient, ResponseError

if TYPE_CHECKING:
    from core_engine.prompt_compressor import PromptCompressor

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemma4:31b-cloud"


class LLMManager:
    """
    Reasoning LLM interface backed by the official Ollama Python library.

    Uses AsyncClient so it integrates naturally with the existing asyncio
    event loop used by FractalReasoner, LogicValidator, AutoResearcher, etc.

    Default model: gemma4:31b-cloud (Ollama cloud-offloaded inference).
    Any call can override the model via the `model` kwarg.
    """

    def __init__(self, host: str = "http://localhost:11434"):
        self._client = AsyncClient(host=host)
        self.default_model = DEFAULT_MODEL

    async def generate_response(self, prompt: str, model: str | None = None) -> str | None:
        """
        Send a single prompt and return the full response string.

        Args:
            prompt : The full prompt string (system + user combined, or plain user).
            model  : Override the default model for this call.

        Returns:
            The assistant's response text, or None on error.
        """
        target_model = model or self.default_model

        messages = [{"role": "user", "content": prompt}]

        try:
            full_response = ""
            async for part in await self._client.chat(
                model=target_model,
                messages=messages,
                stream=True,
            ):
                chunk = part.message.content
                if chunk:
                    full_response += chunk

            logger.debug(f"[LLMManager] {target_model} → {len(full_response)} chars")
            return full_response.strip() or None

        except ResponseError as e:
            logger.error(f"[LLMManager] Ollama ResponseError (model={target_model}): {e.error}")
            if e.status_code == 404:
                logger.info(f"[LLMManager] Model not found locally — pulling {target_model} …")
                try:
                    from ollama import AsyncClient as _AC
                    ac = _AC(host=self._client._client.base_url)
                    await ac.pull(target_model)
                    logger.info(f"[LLMManager] Pull complete. Retry the call manually.")
                except Exception as pull_err:
                    logger.error(f"[LLMManager] Pull failed: {pull_err}")
            return None

        except Exception as e:
            logger.error(f"[LLMManager] Unexpected error (model={target_model}): {e}")
            return None

    async def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        stream: bool = False,
    ) -> str | None:
        """
        Lower-level multi-turn chat call for callers that maintain their own
        message history (e.g. a future multi-turn sparring loop).

        Args:
            messages : Full message list [{"role": ..., "content": ...}, ...]
            model    : Override default model.
            stream   : If True, prints streamed chunks to stdout (debug use).

        Returns:
            Complete assistant reply as a single string.
        """
        target_model = model or self.default_model

        try:
            full_response = ""
            async for part in await self._client.chat(
                model=target_model,
                messages=messages,
                stream=True,
            ):
                chunk = part.message.content
                if chunk:
                    full_response += chunk
                    if stream:
                        print(chunk, end="", flush=True)

            if stream:
                print()  # newline after streaming
            return full_response.strip() or None

        except ResponseError as e:
            logger.error(f"[LLMManager] Chat ResponseError: {e.error}")
            return None
        except Exception as e:
            logger.error(f"[LLMManager] Chat error: {e}")
            return None

    async def embed(self, text: str | list[str], model: str | None = None) -> list | None:
        """
        Generate embeddings via Ollama for future VaultBridge projection.
        Returns a list of float vectors (one per input string).
        """
        target_model = model or self.default_model
        try:
            response = await self._client.embed(model=target_model, input=text)
            return response.embeddings
        except Exception as e:
            logger.error(f"[LLMManager] Embed error: {e}")
            return None

    async def list_models(self) -> list[str]:
        """Returns names of all locally available Ollama models."""
        try:
            result = await self._client.list()
            return [m.model for m in result.models]
        except Exception as e:
            logger.error(f"[LLMManager] list_models error: {e}")
            return []

    async def generate_with_vault_context(
        self,
        prompt: str,
        compressor: "PromptCompressor",
        model: str | None = None,
        run_backward_pass: bool = True,
    ) -> dict:
        """
        VaultBridge call — full round-trip compression.

        Forward pass:
          1. PromptCompressor.compress_query(prompt) → reasoning scaffold
          2. LLM receives scaffold (vault context + query) instead of raw prompt
          3. Slow weights reason WITHIN pre-loaded vault facts

        Backward pass (if run_backward_pass=True):
          4. PromptCompressor.compress_reasoning(response) → Hebbian update
          5. neurons.json updated — vault learns from every inference

        Returns:
          {
            "response"        : str          — LLM output
            "scaffold"        : str          — what was fed to the LLM
            "seeds"           : list[str]    — vault seeds matched
            "cluster"         : list[str]    — activated cluster
            "gaps"            : list[str]    — concepts LLM had to infer
            "match_score"     : float        — seed extraction confidence
            "updated_neurons" : list[str]    — synapses reinforced (if backward)
            "new_neurons"     : list[str]    — stub neurons created (if backward)
          }
        """
        # ── Forward: compress prompt → scaffold ────────────────────────────
        compression_result = await compressor.compress_query(prompt)
        scaffold           = compression_result["scaffold"]

        logger.info(
            f"[LLMManager] VaultBridge → "
            f"seeds={compression_result['seeds']} "
            f"cluster={len(compression_result['cluster'])} neurons "
            f"gaps={compression_result['gaps'][:3]}"
        )

        import time
        start_time = time.time()
        
        # ── LLM call with vault-enriched scaffold ──────────────────────────
        response = await self.generate_response(scaffold, model=model)
        
        latency = time.time() - start_time
        
        # Report latency to Supabase
        from core_engine.reporter import reporter
        asyncio.create_task(reporter.log_event("INFERENCE_PERFORMANCE", {
            "latency_seconds": round(latency, 3),
            "prompt_length": len(prompt),
            "response_length": len(response) if response else 0
        }))

        # ── Backward: compress LLM reasoning back into vault ──────────────
        updated_neurons, new_neurons = [], []
        if run_backward_pass and response:
            backward_result = compressor.compress_reasoning(response, prompt)
            updated_neurons = backward_result["updated_neurons"]
            new_neurons     = backward_result["new_neurons"]

        return {
            "response"        : response,
            "scaffold"        : scaffold,
            "seeds"           : compression_result["seeds"],
            "cluster"         : compression_result["cluster"],
            "gaps"            : compression_result["gaps"],
            "match_score"     : compression_result["match_score"],
            "updated_neurons" : updated_neurons,
            "new_neurons"     : new_neurons,
            "trace"           : compression_result.get("trace", {}),
            "trace_id"        : compression_result.get("trace_id", "TRACE-unknown"),
        }

