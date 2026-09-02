"""
Hand-rolled tool-calling loop (deliberately not a framework like
LangGraph) -- this is worth explaining in an interview: a hand-rolled
loop demonstrates you understand the control flow (plan -> call tool
-> observe -> repeat -> respond) rather than treating agent behaviour
as a black box import.

Uses Gemini (free tier: 1,500 requests/day on Flash, no billing method
required) rather than OpenAI, which has no reliable free tier as of
2026. Function calling is done manually (JSON-schema tool declarations,
parsed function_call parts) rather than via the SDK's automatic
function-calling feature, to keep this loop's control flow explicit and
match the "hand-rolled, not a black box" design goal above.
"""
import json

from google import genai
from google.genai import types

from app.agent.tools import TOOL_REGISTRY
from app.core.config import settings

SYSTEM_PROMPT = """You are BudgetBasket AI, a grocery budgeting assistant for Australian
households. Given a user's budget and usual purchases, build a shopping basket that stays
within budget while staying close to their usual habits. Use the available tools to run the
actual optimization and retrieve grounded substitution facts -- never invent prices or
nutrition claims yourself. Explain each swap in one short sentence citing the retrieved fact."""

TOOLS = [
    types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="run_budget_optimizer",
                description="Run the LP optimizer to pick a basket within budget.",
                parameters={
                    "type": "OBJECT",
                    "properties": {"budget": {"type": "NUMBER"}},
                    "required": ["budget"],
                },
            ),
            types.FunctionDeclaration(
                name="find_substitutes",
                description="Find cheaper substitutes for a given product.",
                parameters={
                    "type": "OBJECT",
                    "properties": {"product_id": {"type": "INTEGER"}},
                    "required": ["product_id"],
                },
            ),
            types.FunctionDeclaration(
                name="retrieve_savings_tips",
                description="Retrieve grounded savings/substitution facts relevant to a query.",
                parameters={
                    "type": "OBJECT",
                    "properties": {"query": {"type": "STRING"}},
                    "required": ["query"],
                },
            ),
        ]
    )
]


class BudgetAgent:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

    def run(self, user_message: str, context: dict, max_steps: int = 5) -> str:
        contents = [
            types.Content(
                role="user",
                parts=[types.Part(text=f"Context: {json.dumps(context)}\n\nRequest: {user_message}")],
            )
        ]

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=TOOLS,
            # Manual function calling -- see module docstring.
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

        for _ in range(max_steps):
            resp = self.client.models.generate_content(model=settings.LLM_MODEL, contents=contents, config=config)
            candidate = resp.candidates[0]
            contents.append(candidate.content)

            function_calls = [p.function_call for p in candidate.content.parts if p.function_call]
            if not function_calls:
                return resp.text or ""

            response_parts = []
            for call in function_calls:
                tool_fn = TOOL_REGISTRY.get(call.name)
                args = dict(call.args) if call.args else {}
                result = tool_fn(**args, **self._extra_args(call.name, context)) if tool_fn else {"error": "unknown tool"}
                response_parts.append(
                    types.Part.from_function_response(name=call.name, response={"result": result})
                )

            contents.append(types.Content(role="user", parts=response_parts))

        return "Reached max reasoning steps without a final answer."

    @staticmethod
    def _extra_args(fn_name: str, context: dict) -> dict:
        """Inject non-LLM-visible args (e.g. full candidate list) the model shouldn't have to pass verbatim."""
        if fn_name == "run_budget_optimizer":
            return {"candidates": context.get("candidates", [])}
        if fn_name == "find_substitutes":
            return {"products": context.get("products", [])}
        return {}
