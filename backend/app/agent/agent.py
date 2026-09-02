"""
Hand-rolled tool-calling loop (deliberately not a framework like
LangGraph) -- this is worth explaining in an interview: a hand-rolled
loop demonstrates you understand the control flow (plan -> call tool
-> observe -> repeat -> respond) rather than treating agent behaviour
as a black box import.
"""
import json

from openai import OpenAI

from app.agent.tools import TOOL_REGISTRY
from app.core.config import settings

SYSTEM_PROMPT = """You are BudgetBasket AI, a grocery budgeting assistant for Australian
households. Given a user's budget and usual purchases, build a shopping basket that stays
within budget while staying close to their usual habits. Use the available tools to run the
actual optimization and retrieve grounded substitution facts -- never invent prices or
nutrition claims yourself. Explain each swap in one short sentence citing the retrieved fact."""

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "run_budget_optimizer",
            "description": "Run the LP optimizer to pick a basket within budget.",
            "parameters": {
                "type": "object",
                "properties": {
                    "budget": {"type": "number"},
                },
                "required": ["budget"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_substitutes",
            "description": "Find cheaper substitutes for a given product.",
            "parameters": {
                "type": "object",
                "properties": {"product_id": {"type": "integer"}},
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "retrieve_savings_tips",
            "description": "Retrieve grounded savings/substitution facts relevant to a query.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
]


class BudgetAgent:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def run(self, user_message: str, context: dict, max_steps: int = 5) -> str:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Context: {json.dumps(context)}\n\nRequest: {user_message}"},
        ]

        for _ in range(max_steps):
            resp = self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
            )
            msg = resp.choices[0].message
            messages.append(msg.model_dump(exclude_none=True))

            if not msg.tool_calls:
                return msg.content or ""

            for call in msg.tool_calls:
                fn_name = call.function.name
                args = json.loads(call.function.arguments)
                tool_fn = TOOL_REGISTRY.get(fn_name)
                result = tool_fn(**args, **self._extra_args(fn_name, context)) if tool_fn else {"error": "unknown tool"}
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(result, default=str),
                    }
                )

        return "Reached max reasoning steps without a final answer."

    @staticmethod
    def _extra_args(fn_name: str, context: dict) -> dict:
        """Inject non-LLM-visible args (e.g. full candidate list) the model shouldn't have to pass verbatim."""
        if fn_name == "run_budget_optimizer":
            return {"candidates": context.get("candidates", [])}
        if fn_name == "find_substitutes":
            return {"products": context.get("products", [])}
        return {}
