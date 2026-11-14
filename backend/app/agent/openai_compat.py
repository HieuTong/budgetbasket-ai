"""Lets the agent talk to any OpenAI-compatible server (vLLM, SGLang, Ollama, hosted APIs).

The agent loop was written against the Gemini SDK. Rather than rewrite the loop and
every test that scripts it, this adapter presents the same small surface the loop uses
(`client.models.generate_content(...)`) and translates in both directions:

    Gemini-style request  ->  OpenAI chat-completions request
    OpenAI response       ->  Gemini-style response

So switching provider is configuration (LLM_PROVIDER, LLM_BASE_URL, LLM_MODEL), and the
tool loop, tracing, retries and evaluations run unchanged against either backend.
"""
import json
import os
from types import SimpleNamespace
from typing import Callable

import requests
from google.genai import types


def _json_schema(schema) -> dict:
    """Gemini tool schemas use upper-case type names ("OBJECT"); JSON Schema uses lower-case."""
    if schema is None:
        return {"type": "object", "properties": {}}
    raw = schema if isinstance(schema, dict) else schema.model_dump(exclude_none=True, mode="json")

    def lower_types(node):
        if isinstance(node, dict):
            return {
                key: (value.lower() if key == "type" and isinstance(value, str) else lower_types(value))
                for key, value in node.items()
            }
        if isinstance(node, list):
            return [lower_types(item) for item in node]
        return node

    return lower_types(raw)


def to_openai_tools(tools) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": declaration.name,
                "description": declaration.description or "",
                "parameters": _json_schema(declaration.parameters),
            },
        }
        for tool in tools or []
        for declaration in tool.function_declarations or []
    ]


def to_openai_messages(contents, system_instruction: str | None) -> list[dict]:
    """Turn the agent's conversation into OpenAI chat messages.

    OpenAI links each tool result to the call that asked for it with an id; Gemini links
    them by order. Ids are therefore generated here by position ("call_0", "call_1", ...),
    and each result takes the oldest unanswered call with the same tool name.
    """
    messages: list[dict] = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})

    next_id = 0
    unanswered: list[tuple[str, str]] = []  # (tool name, call id), oldest first

    for content in contents:
        parts = content.parts or []
        calls = [part.function_call for part in parts if part.function_call]
        results = [part.function_response for part in parts if part.function_response]
        text = "".join(part.text for part in parts if getattr(part, "text", None))

        if results:
            for result in results:
                match = next((pair for pair in unanswered if pair[0] == result.name), None)
                if match is None:
                    continue  # a result with no matching call would be rejected by the server
                unanswered.remove(match)
                messages.append({
                    "role": "tool",
                    "tool_call_id": match[1],
                    "content": json.dumps(result.response, default=str),
                })
        elif calls:
            tool_calls = []
            for call in calls:
                call_id = f"call_{next_id}"
                next_id += 1
                unanswered.append((call.name, call_id))
                tool_calls.append({
                    "id": call_id,
                    "type": "function",
                    "function": {"name": call.name, "arguments": json.dumps(dict(call.args or {}))},
                })
            messages.append({"role": "assistant", "content": text or None, "tool_calls": tool_calls})
        elif text:
            role = "assistant" if content.role == "model" else "user"
            messages.append({"role": role, "content": text})

    return messages


def from_openai_response(data: dict):
    """Wrap an OpenAI response in the shape the agent loop reads from Gemini."""
    message = data["choices"][0]["message"]
    parts = []

    if message.get("content"):
        parts.append(types.Part(text=message["content"]))

    for tool_call in message.get("tool_calls") or []:
        function = tool_call["function"]
        try:
            args = json.loads(function.get("arguments") or "{}")
        except json.JSONDecodeError:
            # Small models sometimes emit broken JSON. Empty args make the tool fail with a
            # clear error, which the loop reports back to the model and records in the trace.
            args = {}
        if not isinstance(args, dict):
            args = {}
        parts.append(types.Part(function_call=types.FunctionCall(name=function["name"], args=args)))

    if not parts:
        parts.append(types.Part(text=""))

    usage = data.get("usage") or {}
    return SimpleNamespace(
        candidates=[SimpleNamespace(content=types.Content(role="model", parts=parts))],
        usage_metadata=SimpleNamespace(
            prompt_token_count=usage.get("prompt_tokens", 0),
            candidates_token_count=usage.get("completion_tokens", 0),
        ),
    )


class _Models:
    def __init__(self, base_url: str, api_key: str, timeout_s: float, post: Callable):
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._api_key = api_key
        self._timeout_s = timeout_s
        self._post = post

    def generate_content(self, model: str, contents, config):
        payload = {
            "model": model,
            "messages": to_openai_messages(contents, getattr(config, "system_instruction", None)),
            "temperature": float(os.getenv("AGENT_TEMPERATURE", "0")),
            "max_tokens": int(os.getenv("AGENT_MAX_OUTPUT_TOKENS", "1024")),
        }
        tools = to_openai_tools(getattr(config, "tools", None))
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        response = self._post(self._url, json=payload, headers=headers, timeout=self._timeout_s)

        if response.status_code >= 400:
            # The status code leads the message because the agent's retry logic reads it:
            # 429 means stop, 503 means try again.
            raise RuntimeError(f"{response.status_code} from LLM server: {response.text[:200]}")

        return from_openai_response(response.json())


class OpenAICompatClient:
    """Drop-in replacement for the Gemini client, for OpenAI-compatible servers."""

    def __init__(self, base_url: str, api_key: str = "", timeout_s: float = 30.0, post: Callable | None = None):
        if not base_url:
            raise RuntimeError("LLM_BASE_URL must be set when LLM_PROVIDER is 'openai'")
        # `post` can be replaced in tests, so they run without a network or a GPU.
        self.models = _Models(base_url, api_key, timeout_s, post or requests.post)
