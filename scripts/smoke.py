"""Send real OpenAI SDK requests through a local AgentWarden proxy."""

from __future__ import annotations

import json
import os
import sys
from uuid import uuid4

import httpx
from openai import OpenAI


def main() -> int:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY is required for this real-API smoke test.", file=sys.stderr)
        return 2

    base_url = os.environ.get("AGENTWARDEN_BASE_URL", "http://localhost:8080/v1").rstrip("/")
    model = os.environ.get("AGENTWARDEN_MODEL", "gpt-5.6-terra")
    session_id = os.environ.get("AGENTWARDEN_SESSION_ID", f"smoke-{uuid4().hex[:8]}")
    client = OpenAI(api_key=api_key, base_url=base_url)
    headers = {"X-AgentWarden-Session": session_id}
    messages = [
        {"role": "system", "content": "Reply concisely."},
        {"role": "user", "content": "Say hello from AgentWarden."},
    ]

    non_streaming = client.chat.completions.create(
        model=model,
        messages=messages,
        extra_headers=headers,
    )
    print("Non-streaming response:")
    print(non_streaming.choices[0].message.content or "")

    print("\nStreaming response:")
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
    print()

    proxy_root = base_url.removesuffix("/v1")
    stats = httpx.get(
        f"{proxy_root}/stats",
        params={"session_id": session_id},
        timeout=10.0,
    )
    stats.raise_for_status()
    print("\nTrace stats:")
    print(json.dumps(stats.json(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
