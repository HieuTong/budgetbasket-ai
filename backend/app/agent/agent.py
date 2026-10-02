import json
import time
from google import genai
from google.genai import types

from app.agent.tools import TOOL_REGISTRY
from app.core.config import settings
from app.ml.optimizer import BasketItem
from app.ml.similarity import Product

SYSTEM_PROMPT = (
    "You are BudgetBasket AI, a grocery budgeting assistant for Australian households.\n\n"
    "Use the user's catalog and purchase context.\n\n"
    "When asked to optimize a basket, call the actual optimizer tool rather than doing arithmetic "
    "yourself.\n\n"
    "When the user asks whether to buy, wait, or make a purchasing decision for a specific product, "
    "call the make_product_decision tool. Do not make the BUY, WAIT, SUBSTITUTE, or NO_ACTION decision yourself.\n\n"
    "When the user asks for cheaper alternatives or substitution advice, call find_substitutes.\n\n"
    "When the user asks how to save money or wants savings advice, call retrieve_savings_tips.\n\n"
    "When multiple requested tools are independent, request all relevant tools in the same response "
    "instead of waiting for one tool result before requesting another.\n\n"
    "For example, if the user asks for a purchasing decision and cheaper substitutes, call "
    "make_product_decision and find_substitutes together. If savings advice is also requested, "
    "call retrieve_savings_tips together with them.\n\n"
    "Never invent prices, products, purchase history, or nutrition claims. Do not treat retrieved "
    "knowledge as a replacement for real product prices or DecisionOS results.\n\n"
    "Explain recommendations using facts returned by the tools.\n"
)



TOOLS = [
    types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="run_budget_optimizer",
                description=(
                    "Run the LP optimizer over the user's catalog "
                    "within a budget."
                ),
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "budget": {
                            "type": "NUMBER",
                        },
                    },
                    "required": ["budget"],
                },
            ),
            types.FunctionDeclaration(
                name="find_substitutes",
                description=(
                    "Find cheaper substitutes for a product "
                    "in the user's catalog."
                ),
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "product_id": {
                            "type": "INTEGER",
                        },
                    },
                    "required": ["product_id"],
                },
            ),
            types.FunctionDeclaration(
                name="make_product_decision",
                description=(
                    "Generate a deterministic BUY, WAIT, or NO_ACTION "
                    "decision for a product using real price history, "
                    "price-direction probabilities, forecasting, "
                    "and DecisionOS."
                ),
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "product_id": {
                            "type": "INTEGER",
                            "description": "Database product ID.",
                        },
                    },
                    "required": ["product_id"],
                },
            ),
            types.FunctionDeclaration(
                name="retrieve_savings_tips",
                description=(
                    "Retrieve grounded savings and substitution "
                    "facts relevant to a query."
                ),
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "query": {
                            "type": "STRING",
                        },
                    },
                    "required": ["query"],
                },
            ),
        ]
    )
]


class BudgetAgent:
    def __init__(self):
        self.client = genai.Client(
            api_key=settings.GEMINI_API_KEY
        )

    def run(
        self,
        user_message: str,
        context: dict,
        db,
        max_steps: int = 5,
    ) -> str:
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part(
                        text=(
                            f"Context: {json.dumps(context)}"
                            f"\n\nRequest: {user_message}"
                        )
                    )
                ],
            )
        ]

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=TOOLS,
            automatic_function_calling=(
                types.AutomaticFunctionCallingConfig(
                    disable=True
                )
            ),
        )

        for _ in range(max_steps):
            resp = None

            for attempt in range(2):
                try:
                    resp = self.client.models.generate_content(
                        model=settings.LLM_MODEL,
                        contents=contents,
                        config=config,
                    )
                    break
                except Exception as exc:
                    if attempt == 1:
                        print(
                            f"[Agent] Gemini request failed: {exc}"
                        )
                        return (
                            "I could not complete the request because "
                            "the AI service is temporarily unavailable."
                        )

                    print(
                        "[Agent] Gemini temporarily unavailable. "
                        "Retrying..."
                    )
                    time.sleep(1)

            candidate = resp.candidates[0]
            contents.append(candidate.content)

            function_calls = [
                part.function_call
                for part in candidate.content.parts
                if part.function_call
            ]

            if not function_calls:
                return resp.text or ""

            response_parts = []

            for call in function_calls:
                tool_fn = TOOL_REGISTRY.get(call.name)
                args = (
                    dict(call.args)
                    if call.args
                    else {}
                )

                extra_args = self._extra_args(
                    call.name,
                    context,
                    db,
                )

                if tool_fn:
                    print(
                        f"[Agent] Tool: {call.name}"
                    )
                    print(
                        f"[Agent] Args: {args}"
                    )

                    result = tool_fn(
                        **args,
                        **extra_args,
                    )

                    if isinstance(result, dict):
                        print(
                            f"[Agent] Result: {result.get('decision', 'completed')}"
                        )
                    else:
                        print(
                            "[Agent] Result: completed"
                        )
                else:
                    result = {
                        "error": "unknown tool"
                    }

                response_parts.append(
                    types.Part.from_function_response(
                        name=call.name,
                        response={
                            "result": result,
                        },
                    )
                )

            contents.append(
                types.Content(
                    role="user",
                    parts=response_parts,
                )
            )

        return (
            "Reached max reasoning steps "
            "without a final answer."
        )

    @staticmethod
    def _extra_args(
        fn_name: str,
        context: dict,
        db,
    ) -> dict:
        if fn_name == "run_budget_optimizer":
            candidates = [
                (
                    item
                    if isinstance(item, BasketItem)
                    else BasketItem(**item)
                )
                for item in context.get(
                    "candidates",
                    [],
                )
            ]

            return {
                "candidates": candidates,
            }

        if fn_name == "find_substitutes":
            return {
                "db": db,
            }

        if fn_name == "make_product_decision":
            return {
                "db": db,
                "user_id": context.get("user_id"),
            }

        return {}