"""
DeepEvalBaseLLM adapter wrapping VAPE's own multi-provider LLM layer
(agents/llm.py — Groq/Cerebras/OpenRouter/GitHub Models/Together, all free
tier). deepteam's red_team() needs a `simulator_model` (writes attacks) and
an `evaluation_model` (judges whether the target was compromised); both
default to OpenAI models, which VAPE doesn't have a key for and won't pay
for. This adapter lets deepteam campaigns run entirely on VAPE's existing
free-tier stack — zero new secrets, zero new cost.

Honesty note (documented, not hidden): using VAPE's own small open-source
model as both attacker and judge is weaker than using a stronger frontier
model as judge — it can miss subtler jailbreaks. A FAIL from this setup is
still strong evidence of a real vulnerability (the target model produced
the bad output regardless of who graded it); a PASS is weaker evidence of
true safety and should be read as "held against this test," not "immune."
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from agents.llm import ask_safe, ask_oci_grok_safe  # noqa: E402

from deepeval.models.base_model import DeepEvalBaseLLM


class VapeLLM(DeepEvalBaseLLM):
    """Wraps agents.llm.ask_safe (or ask_oci_grok_safe, see use_oci_grok) as
    a deepteam/deepeval-compatible model.

    provider_order lets a caller pin this to agents.llm.FRONTIER_ORDER — used
    for the judge (see campaign_vape.py), since a stronger judge model
    directly addresses the honesty note above: a smarter judge catches
    subtler jailbreaks the small open models could miss. Left None (the
    default free chain) for the attack simulator, which doesn't need to be
    smart to write attack prompts.

    use_oci_grok routes generate() through ask_oci_grok_safe (OCI-hosted
    Grok 4.3 first, falling back to Vertex/provider_order) instead of plain
    ask_safe — set True only for the judge instance, never the simulator:
    the simulator must stay off VAPE's strongest models by design (it's
    writing attacks, not judging them), enforced by tests/
    test_llm_critical_wiring.py::test_adversarial_simulator_stays_off_frontier_order."""

    def __init__(self, tier="fast", provider_order=None, use_oci_grok=False):
        self.tier = tier
        self.provider_order = provider_order
        self.use_oci_grok = use_oci_grok
        super().__init__(model=f"vape-{tier}")

    def load_model(self):
        return self

    def generate(self, prompt: str, schema=None, *args, **kwargs) -> str:
        # deepteam probes for native structured-output support by passing
        # schema= and catching TypeError to fall back to its own
        # text+trimAndLoadJson extraction (see deepeval's DeepEvalBaseLLM.
        # generate_with_schema). agents.llm has no JSON-mode/function-calling
        # support, so we must actually raise here — silently accepting and
        # ignoring schema (e.g. via **kwargs) breaks that fallback contract:
        # callers would get a plain string back where a schema object with a
        # `.data` attribute was expected. The prompt text deepteam sends
        # already contains its own JSON-format instructions for exactly this
        # non-native-schema path.
        if schema is not None:
            raise TypeError("VapeLLM has no native structured-output support")
        ask_fn = ask_oci_grok_safe if self.use_oci_grok else ask_safe
        text, provider = ask_fn(
            system="You are a precise, technical assistant. Follow the instructions exactly.",
            user=prompt,
            tier=self.tier,
            temperature=0.7,
            max_tokens=1024,
            provider_order=self.provider_order,
        )
        if (text or "").startswith("[llm unavailable"):
            raise RuntimeError(text)
        return text

    async def a_generate(self, prompt: str, schema=None, *args, **kwargs) -> str:
        if schema is not None:
            raise TypeError("VapeLLM has no native structured-output support")
        # agents.llm.ask_safe is sync (urllib); deepteam's async_mode expects
        # an awaitable, so run the sync call off the event loop thread.
        import asyncio
        return await asyncio.to_thread(self.generate, prompt)

    def get_model_name(self) -> str:
        return f"vape-{self.tier} (agents.llm multi-provider)"
