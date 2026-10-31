import json
import os
import random
import time
from google import genai
from google.genai import types

from app.agent.tools import TOOL_REGISTRY
from app.agent.tracing import AgentTrace, LLMCall, ToolCall
from app.core.config import settings
from app.ml.optimizer import BasketItem
from app.services.basket import MAX_DISTINCT_PRODUCTS
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
    "When the user names a product (for example 'milk') instead of giving a product ID, call "
    "find_products first and use the product_id it returns. If several products match, use the "
    "closest match and say which one you used.\n\n"
    "When the user asks how a price has changed or why something costs more, call "
    "explain_price_trend. Describe what the data shows. Never invent reasons such as inflation "
    "or supply problems: the data shows what changed, not why.\n\n"
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
                name="find_products",
                description=(
                    "Search the catalogue by name and return matching products "
                    "with their product_id and price."
                ),
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "query": {
                            "type": "STRING",
                            "description": "Product name, e.g. 'milk' or 'wholemeal bread'.",
                        },
                    },
                    "required": ["query"],
                },
            ),
            types.FunctionDeclaration(
                name="explain_price_trend",
                description=(
                    "Recent price history and trend for one product, "
                    "from historical transaction data."
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
    def __init__(self, client=None, tool_registry: dict | None = None):
        # Injecting the client and tools lets tests and evaluations run without network calls.
        # A hard timeout per model call stops one slow request from hanging for a minute or more.
        timeout_ms = int(float(os.getenv("AGENT_LLM_TIMEOUT_S", "30")) * 1000)
        self.client = client or genai.Client(
            api_key=settings.GEMINI_API_KEY,
            http_options=types.HttpOptions(timeout=timeout_ms),
        )
        self.tool_registry = tool_registry or TOOL_REGISTRY

    def run(
        self,
        user_message: str,
        context: dict,
        db,
        max_steps: int = 5,
        trace: AgentTrace | None = None,
    ) -> str:
        trace = trace if trace is not None else AgentTrace()
        started = time.perf_counter()
        answer = self._run(user_message, context, db, max_steps, trace)
        trace.final_answer = answer
        trace.total_latency_s = round(time.perf_counter() - started, 3)
        return answer

    def _run(
        self,
        user_message: str,
        context: dict,
        db,
        max_steps: int,
        trace: AgentTrace,
    ) -> str:
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part(
                        text=(
                            f"Context: {json.dumps(self._prompt_context(context))}"
                            f"\n\nRequest: {user_message}"
                        )
                    )
                ],
            )
        ]

        # Optional: limit "thinking" for fast tool routing. Unset = the model's default.
        thinking_budget = os.getenv("AGENT_THINKING_BUDGET")
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=TOOLS,
            automatic_function_calling=(
                types.AutomaticFunctionCallingConfig(
                    disable=True
                )
            ),
            thinking_config=(
                types.ThinkingConfig(thinking_budget=int(thinking_budget))
                if thinking_budget is not None
                else None
            ),
        )

        for _ in range(max_steps):
            resp = None

            max_attempts = int(os.getenv("AGENT_LLM_ATTEMPTS", "3"))

            for attempt in range(max_attempts):
                try:
                    call_started = time.perf_counter()
                    resp = self.client.models.generate_content(
                        model=settings.LLM_MODEL,
                        contents=contents,
                        config=config,
                    )
                    usage = getattr(resp, "usage_metadata", None)
                    trace.llm_calls.append(LLMCall(
                        latency_s=round(time.perf_counter() - call_started, 3),
                        prompt_tokens=int(getattr(usage, "prompt_token_count", 0) or 0),
                        output_tokens=int(getattr(usage, "candidates_token_count", 0) or 0),
                    ))
                    break
                except Exception as exc:
                    error_text = str(exc)

                    trace.error = error_text[:300]

                    if "429" in error_text:
                        print(
                            f"[Agent] Gemini quota exhausted: {exc}"
                        )
                        return (
                            "The AI service quota has been reached. "
                            "Please try again after the quota resets."
                        )

                    retryable = (
                        "503" in error_text
                        or "timed out" in error_text.lower()
                        or "timeout" in type(exc).__name__.lower()
                    )

                    if not retryable:
                        print(
                            f"[Agent] Gemini request failed: {exc}"
                        )
                        return (
                            "I could not complete the request because "
                            "the AI service is temporarily unavailable."
                        )

                    if attempt == max_attempts - 1:
                        print(
                            f"[Agent] Gemini request failed after retry: {exc}"
                        )
                        return (
                            "The AI service is temporarily unavailable. "
                            "Please try again shortly."
                        )

                    print(
                        "[Agent] Gemini temporarily unavailable. "
                        "Retrying..."
                    )
                    # Exponential backoff with jitter: wait longer each time, and randomly,
                    # so many clients don't all retry at the same instant.
                    time.sleep(min(8.0, 2.0 ** (attempt + 1)) * random.uniform(0.5, 1.0))

            candidate = resp.candidates[0]
            contents.append(candidate.content)

            function_calls = [
                part.function_call
                for part in candidate.content.parts
                if part.function_call
            ]

            if not function_calls:
                # Join text parts ourselves: thinking models also return non-text parts.
                return "".join(
                    part.text
                    for part in candidate.content.parts
                    if getattr(part, "text", None)
                )

            response_parts = []

            for call in function_calls:
                tool_fn = self.tool_registry.get(call.name)
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

                    tool_started = time.perf_counter()
                    try:
                        result = tool_fn(
                            **args,
                            **extra_args,
                        )
                        ok = True
                    except Exception as exc:
                        # A failing tool must not crash the request: report it to the model and the trace.
                        result = {"error": f"{call.name} failed: {exc}"}
                        ok = False
                    trace.tool_calls.append(ToolCall(
                        name=call.name,
                        args=args,
                        latency_s=round(time.perf_counter() - tool_started, 3),
                        ok=ok,
                        result=result,
                    ))

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
                    trace.tool_calls.append(ToolCall(
                        name=call.name, args=args, latency_s=0.0, ok=False, result=result,
                    ))

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
    def _prompt_context(context: dict) -> dict:
        """What the model sees. Candidate products go to the optimiser tool, not into the prompt:
        the model doesn't need them, and sending the whole catalogue costs tokens and
        widens the surface for prompt injection through product names."""
        visible = {k: v for k, v in context.items() if k != "candidates"}
        if "candidates" in context:
            visible["candidate_product_count"] = len(context["candidates"])
        return visible

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
                "max_distinct_products": MAX_DISTINCT_PRODUCTS,
            }

        if fn_name in ("find_substitutes", "find_products", "explain_price_trend"):
            return {
                "db": db,
            }

        if fn_name == "make_product_decision":
            return {
                "db": db,
                "user_id": context.get("user_id"),
            }

        return {}
