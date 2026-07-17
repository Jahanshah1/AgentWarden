"""Send real OpenAI SDK requests through a local AgentWarden proxy."""

from __future__ import annotations

import json
import os
import sys
from uuid import uuid4

import httpx
from openai import APIConnectionError, APIStatusError, OpenAI


def main() -> int:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY is required for this real-API smoke test.", file=sys.stderr)
        return 2

    base_url = os.environ.get("AGENTWARDEN_BASE_URL", "http://localhost:8080/v1").rstrip("/")
    model = os.environ.get("AGENTWARDEN_MODEL", "gpt-5.6-terra")
    session_id = os.environ.get("AGENTWARDEN_SESSION_ID", f"smoke-{uuid4().hex[:8]}")
    proxy_root = base_url.removesuffix("/v1")
    if not _proxy_is_running(proxy_root):
        return 1

    client = OpenAI(api_key=api_key, base_url=base_url)
    headers = {"X-AgentWarden-Session": session_id}
    messages = [
        {"role": "system", "content": "Reply concisely."},
        {"role": "user", "content": "Say hello from AgentWarden."},
    ]

    try:
        non_streaming = client.chat.completions.create(
            model=model,
            messages=messages,
            extra_headers=headers,
        )
    except APIConnectionError:
        print(
            "AgentWarden was reachable, but it could not connect to OpenAI. "
            "Check your network connection and try again.",
            file=sys.stderr,
        )
        return 1
    except APIStatusError as error:
        _print_api_error(error)
        return 1

    print("Non-streaming response:")
    print(non_streaming.choices[0].message.content or "")

    print("\nStreaming response:")
    try:
        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            stream_options={"include_usage": True},
            extra_headers=headers,
        )
        for chunk in stream:
            if chunk.choices:
                content = chunk.choices[0].delta.content
                if content:
                    print(content, end="", flush=True)
    except APIConnectionError:
        print("\nThe streaming request could not reach OpenAI.", file=sys.stderr)
        return 1
    except APIStatusError as error:
        print()
        _print_api_error(error)
        return 1
    print()

    try:
        stats = httpx.get(
            f"{proxy_root}/stats",
            params={"session_id": session_id},
            timeout=10.0,
        )
        stats.raise_for_status()
    except httpx.HTTPError:
        print(
            "The OpenAI requests completed, but AgentWarden stats could not be read.",
            file=sys.stderr,
        )
        return 1
    print("\nTrace stats:")
    print(json.dumps(stats.json(), indent=2))
    return 0


def _proxy_is_running(proxy_root: str) -> bool:
    try:
        response = httpx.get(f"{proxy_root}/stats", timeout=2.0)
    except httpx.HTTPError:
        print(
            f"AgentWarden is not running at {proxy_root}.\n"
            "In another terminal, run:\n"
            "  .venv/bin/uvicorn proxy.server:app --port 8080",
            file=sys.stderr,
        )
        return False
    if response.is_success:
        return True
    print(
        f"AgentWarden responded with HTTP {response.status_code} at {proxy_root}.\n"
        "Check the terminal where Uvicorn is running for details.",
        file=sys.stderr,
    )
    return False


def _print_api_error(error: APIStatusError) -> None:
    """Show the API's safe status message without exposing credentials."""

    detail = error.response.text.strip()
    print(f"OpenAI returned HTTP {error.status_code}: {detail}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
