"""
Hand-rolled Gemini tool-calling loop.

The LLM plans tool calls and explains results. Deterministic computation stays
in application services and DecisionOS rather than being delegated to the model.
"""
import json

from google import genai
from google.genai import types

from app.agent.tools import TOOL_REGISTRY
from app.core.config import settings
from app.ml.optimizer import BasketItem
from app.ml.similarity import Product

SYSTEM_PROMPT = """You are BudgetBasket AI, a grocery budgeting assistant for Australian
households. Use the user's catalog and purchase context. When asked to optimize, call the
actual optimizer tool rather than doing arithmetic yourself. Never invent prices, products,
purchase history, or nutrition claims. Explain recommendations using facts returned by tools."""

TOOLS = [
    types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="run_budget_optimizer",
                description="Run the LP optimizer over the user's catalog within a budget.",
                parameters={
                    "type": "OBJECT",
                    "properties": {"budget": {"type": "NUMBER"}},
                    "required": ["budget"],
                },
            ),
            types.FunctionDeclaration(
                name="find_substitutes",
                description="Find cheaper substitutes for a product in the user's catalog.",
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
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

        for _ in range(max_steps):
            resp = self.client.models.generate_content(
                model=settings.LLM_MODEL,
                contents=contents,
                config=config,
            )
            candidate = resp.candidates[0]
            contents.append(candidate.content)

            function_calls = [
                p.function_call for p in candidate.content.parts if p.function_call
            ]
            if not function_calls:
                return resp.text or ""

            response_parts = []
            for call in function_calls:
                tool_fn = TOOL_REGISTRY.get(call.name)
                args = dict(call.args) if call.args else {}
                extra_args = self._extra_args(call.name, context)
                result = (
                    tool_fn(**args, **extra_args)
                    if tool_fn
                    else {"error": "unknown tool"}
                )
                response_parts.append(
                    types.Part.from_function_response(
                        name=call.name,
                        response={"result": result},
                    )
                )

            contents.append(types.Content(role="user", parts=response_parts))

        return "Reached max reasoning steps without a final answer."

    @staticmethod
    def _extra_args(fn_name: str, context: dict) -> dict:
        if fn_name == "run_budget_optimizer":
            candidates = [
                item if isinstance(item, BasketItem) else BasketItem(**item)
                for item in context.get("candidates", [])
            ]
            return {"candidates": candidates}

        if fn_name == "find_substitutes":
            products = [
                item if isinstance(item, Product) else Product(**item)
                for item in context.get("products", [])
            ]
            return {"products": products}

        return {}
