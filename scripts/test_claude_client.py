"""
Quick smoke-test for ClaudeClient.

Run from the project root:
    python scripts/test_claude_client.py
"""
import logging
import sys
from pathlib import Path

# Allow imports from project root regardless of working directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.llm.claude_client import ClaudeClient, ClaudeRequest

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def test_basic_completion() -> None:
    client = ClaudeClient()

    request = ClaudeRequest(
        system="You are a concise assistant. Reply in one sentence.",
        messages=[{"role": "user", "content": "What is an Investment Committee?"}],
    )

    response = client.complete(request)

    print("\n── Response ──────────────────────────────────────────")
    print(f"Content     : {response.content}")
    print(f"Model       : {response.model}")
    print(f"Tokens      : {response.input_tokens} in / {response.output_tokens} out")
    print(f"Stop reason : {response.stop_reason}")
    print(f"Latency     : {response.latency_ms} ms")
    print("──────────────────────────────────────────────────────\n")

    assert response.content, "Response content must not be empty"
    assert response.input_tokens > 0
    assert response.output_tokens > 0
    print("test_basic_completion PASSED")


def test_missing_api_key() -> None:
    import os
    original = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        ClaudeClient(api_key="")
        print("test_missing_api_key FAILED — expected ValueError")
    except ValueError as exc:
        print(f"test_missing_api_key PASSED ({exc})")
    finally:
        if original:
            os.environ["ANTHROPIC_API_KEY"] = original


if __name__ == "__main__":
    test_missing_api_key()
    test_basic_completion()
