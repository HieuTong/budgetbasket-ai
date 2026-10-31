"""Per-request trace of the agent: every LLM call and tool call, with timing, tokens and cost."""
from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field


@dataclass
class LLMCall:
    latency_s: float
    prompt_tokens: int
    output_tokens: int


@dataclass
class ToolCall:
    name: str
    args: dict
    latency_s: float
    ok: bool
    result: object = None


@dataclass
class AgentTrace:
    llm_calls: list[LLMCall] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    final_answer: str = ""
    total_latency_s: float = 0.0

    @property
    def prompt_tokens(self) -> int:
        return sum(c.prompt_tokens for c in self.llm_calls)

    @property
    def output_tokens(self) -> int:
        return sum(c.output_tokens for c in self.llm_calls)

    @property
    def tools_called(self) -> list[str]:
        return [t.name for t in self.tool_calls]

    def cost_usd(self) -> float | None:
        """Estimated cost, using prices you set as env vars (USD per million tokens).

        Prices change and differ by model, so they are configuration, never hard-coded.
        """
        p_in = os.getenv("LLM_PRICE_INPUT_PER_M")
        p_out = os.getenv("LLM_PRICE_OUTPUT_PER_M")
        if not p_in or not p_out:
            return None
        return (self.prompt_tokens * float(p_in) + self.output_tokens * float(p_out)) / 1_000_000

    def to_dict(self) -> dict:
        d = asdict(self)
        for t in d["tool_calls"]:
            t["result"] = str(t["result"])[:300]  # keep traces small; never log full payloads
        d.update(prompt_tokens=self.prompt_tokens, output_tokens=self.output_tokens, cost_usd=self.cost_usd())
        return d
