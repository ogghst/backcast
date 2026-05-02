"""Test LangChain's native reasoning content support for DeepSeek.

This script verifies whether LangChain's content_blocks property properly
handles DeepSeek's reasoning_content field, which would allow us to remove
the current monkey-patch hacks.

Run with:
    cd backend && source .venv/bin/activate
    uv run pytest tests/ai/test_deepseek_native_support.py -v -s

Or with DeepSeek API key:
    DEEPSEEK_API_KEY=sk-xxx uv run pytest tests/ai/test_deepseek_native_support.py -v -s
"""

import os
import sys
from typing import Any

import pytest
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, AIMessageChunk

# Test configuration
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-reasoner")


def has_deepseek_credentials() -> bool:
    """Check if DeepSeek credentials are available."""
    return bool(DEEPSEEK_API_KEY and DEEPSEEK_API_KEY.startswith("sk-"))


@pytest.mark.skipif(
    not has_deepseek_credentials(),
    reason="DEEPSEEK_API_KEY not set or invalid - set to enable live tests"
)
class TestDeepSeekNativeSupport:
    """Test suite for verifying LangChain's native DeepSeek reasoning support."""

    def test_reasoning_content_in_additional_kwargs(self):
        """Test that reasoning_content appears in additional_kwargs (current hack behavior).

        This verifies the current monkey-patch is working and establishes baseline.
        """
        model = ChatOpenAI(
            model=DEEPSEEK_MODEL,
            api_key=DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com",
            extra_body={"thinking": {"type": "enabled"}},
            streaming=False,
        )

        response = model.invoke("What is 2+2? Keep it brief.")

        # Check if reasoning_content is in additional_kwargs (current hack behavior)
        assert isinstance(response, AIMessage), f"Expected AIMessage, got {type(response)}"

        reasoning_in_kwargs = response.additional_kwargs.get("reasoning_content")
        print(f"\n[TEST] reasoning_content in additional_kwargs: {bool(reasoning_in_kwargs)}")
        if reasoning_in_kwargs:
            print(f"[TEST] reasoning_content length: {len(reasoning_in_kwargs)} chars")
            print(f"[TEST] reasoning_content preview: {reasoning_in_kwargs[:200]}...")

    def test_reasoning_content_in_content_blocks(self):
        """Test if LangChain's native content_blocks exposes reasoning content.

        If this works, we can remove the monkey-patches!
        """
        model = ChatOpenAI(
            model=DEEPSEEK_MODEL,
            api_key=DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com",
            extra_body={"thinking": {"type": "enabled"}},
            streaming=False,
        )

        response = model.invoke("What is the capital of France? Be very brief.")

        # Try to access content_blocks (LangChain native property)
        assert hasattr(response, "content_blocks"), "AIMessage should have content_blocks property"

        content_blocks = list(response.content_blocks) if response.content_blocks else []
        print(f"\n[TEST] content_blocks type: {type(content_blocks)}")
        print(f"[TEST] content_blocks count: {len(content_blocks)}")

        for i, block in enumerate(content_blocks):
            print(f"[TEST] Block {i}: type={block.get('type')}, keys={list(block.keys())}")

        # Check for reasoning blocks
        reasoning_blocks = [b for b in content_blocks if b.get("type") == "reasoning"]
        print(f"\n[TEST] Found {len(reasoning_blocks)} reasoning blocks")

        if reasoning_blocks:
            for i, block in enumerate(reasoning_blocks):
                reasoning = block.get("reasoning", "")
                print(f"[TEST] Reasoning block {i}: {len(reasoning)} chars")
                print(f"[TEST] Preview: {reasoning[:200]}...")

        # Check text block too
        text_blocks = [b for b in content_blocks if b.get("type") == "text"]
        if text_blocks:
            print(f"\n[TEST] Text block: {text_blocks[0].get('text', '')[:100]}...")

        # This is the key test - if reasoning_blocks is non-empty, native support works!
        if reasoning_blocks:
            print("\n[SUCCESS] LangChain native reasoning support detected!")
        else:
            print("\n[FAIL] No reasoning blocks found - monkey-patch still needed")

    def test_streaming_preserves_reasoning_content(self):
        """Test if streaming chunks preserve reasoning_content via content_blocks.

        This verifies the streaming monkey-patch can potentially be removed.
        """
        model = ChatOpenAI(
            model=DEEPSEEK_MODEL,
            api_key=DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com",
            extra_body={"thinking": {"type": "enabled"}},
            streaming=True,
        )

        print("\n[TEST] Starting streaming test...")

        all_reasoning = []
        all_text = []
        chunk_count = 0

        for chunk in model.stream("Count to 5."):
            chunk_count += 1
            if isinstance(chunk, AIMessageChunk):
                # Check content_blocks
                content_blocks = list(chunk.content_blocks) if chunk.content_blocks else []

                reasoning_blocks = [b for b in content_blocks if b.get("type") == "reasoning"]
                text_blocks = [b for b in content_blocks if b.get("type") == "text"]

                for rb in reasoning_blocks:
                    all_reasoning.append(rb.get("reasoning", ""))

                for tb in text_blocks:
                    all_text.append(tb.get("text", ""))

                # Also check additional_kwargs (current hack)
                rc_in_kwargs = chunk.additional_kwargs.get("reasoning_content")
                if rc_in_kwargs:
                    all_reasoning.append(rc_in_kwargs)

        print(f"[TEST] Received {chunk_count} chunks")
        print(f"[TEST] Total reasoning chars from content_blocks: {sum(len(r) for r in all_reasoning)}")
        print(f"[TEST] Total text chars from content_blocks: {sum(len(t) for t in all_text)}")

        if all_reasoning:
            print(f"\n[TEST] Reasoning preview: {all_reasoning[0][:200]}...")
            print("\n[SUCCESS] Streaming preserves reasoning content!")
        else:
            print("\n[FAIL] No reasoning content found in stream")

    def test_raw_api_response_structure(self):
        """Inspect raw API response to understand DeepSeek's response format.

        This helps us understand if the issue is with DeepSeek's format or LangChain's parsing.
        """
        from openai import OpenAI

        client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com",
        )

        print("\n[TEST] Inspecting raw API response...")

        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": "Say hello"}],
            stream=False,
            extra_body={"thinking": {"type": "enabled"}},
        )

        choice = response.choices[0]
        print(f"[TEST] Response structure keys: {dir(choice.message)}")

        # Check for reasoning_content in raw response
        message_dict = choice.message.model_dump()
        print(f"[TEST] Raw message keys: {list(message_dict.keys())}")

        if "reasoning_content" in message_dict:
            print(f"[TEST] Found reasoning_content in raw API response!")
            print(f"[TEST] Length: {len(message_dict['reasoning_content'])} chars")
        else:
            print(f"[TEST] No reasoning_content in raw API response")

        # Check content structure
        if hasattr(choice.message, "content"):
            print(f"[TEST] Content type: {type(choice.message.content)}")
            if isinstance(choice.message.content, list):
                print(f"[TEST] Content is list with {len(choice.message.content)} items")
                for i, item in enumerate(choice.message.content[:3]):
                    print(f"[TEST]   Item {i}: {type(item)} = {item}")


def test_synthetic_reasoning_message():
    """Test with a synthetic AIMessage to verify content_blocks parsing logic.

    This test doesn't require API access and verifies LangChain's parsing
    of different content formats.
    """
    print("\n[TEST] Testing synthetic reasoning message parsing...")

    # Test 1: Reasoning as list of dicts (Anthropic-style)
    msg1 = AIMessage(
        content=[
            {"type": "thinking", "thinking": "Let me think about this..."},
            {"type": "text", "text": "The answer is 42."}
        ],
        response_metadata={"model_provider": "anthropic"}
    )

    blocks1 = list(msg1.content_blocks) if msg1.content_blocks else []
    print(f"[TEST] Anthropic-style: {len(blocks1)} blocks")
    for b in blocks1:
        print(f"[TEST]   {b}")

    # Test 2: Reasoning via additional_kwargs (current DeepSeek hack)
    msg2 = AIMessage(
        content="The answer is 42.",
        additional_kwargs={"reasoning_content": "Let me think about this..."}
    )

    blocks2 = list(msg2.content_blocks) if msg2.content_blocks else []
    print(f"[TEST] additional_kwargs style: {len(blocks2)} blocks")
    for b in blocks2:
        print(f"[TEST]   {b}")

    # Test 3: OpenAI-style reasoning content
    msg3 = AIMessage(
        content=[
            {
                "type": "reasoning",
                "id": "rs_abc123",
                "summary": [
                    {"type": "summary_text", "text": "summary 1"},
                ],
            },
            {"type": "text", "text": "The answer is 42."},
        ],
        response_metadata={"model_provider": "openai"}
    )

    blocks3 = list(msg3.content_blocks) if msg3.content_blocks else []
    print(f"[TEST] OpenAI-style: {len(blocks3)} blocks")
    for b in blocks3:
        print(f"[TEST]   {b}")


if __name__ == "__main__":
    """Run tests directly for quick verification."""
    print("=" * 60)
    print("DeepSeek Native LangChain Support Verification")
    print("=" * 60)

    # Always run synthetic test
    print("\n" + "=" * 60)
    print("Running synthetic tests (no API required)")
    print("=" * 60)
    test_synthetic_reasoning_message()

    # Run live tests if credentials available
    if has_deepseek_credentials():
        print("\n" + "=" * 60)
        print("Running live API tests")
        print("=" * 60)

        test_instance = TestDeepSeekNativeSupport()

        try:
            print("\n--- Test 1: additional_kwargs (baseline) ---")
            test_instance.test_reasoning_content_in_additional_kwargs()
        except Exception as e:
            print(f"[ERROR] Test 1 failed: {e}")

        try:
            print("\n--- Test 2: content_blocks (native support) ---")
            test_instance.test_reasoning_content_in_content_blocks()
        except Exception as e:
            print(f"[ERROR] Test 2 failed: {e}")

        try:
            print("\n--- Test 3: streaming ---")
            test_instance.test_streaming_preserves_reasoning_content()
        except Exception as e:
            print(f"[ERROR] Test 3 failed: {e}")

        try:
            print("\n--- Test 4: raw API response ---")
            test_instance.test_raw_api_response_structure()
        except Exception as e:
            print(f"[ERROR] Test 4 failed: {e}")

        print("\n" + "=" * 60)
        print("Verification complete!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("Skipping live tests - set DEEPSEEK_API_KEY to enable")
        print("=" * 60)
        print("\nExample: DEEPSEEK_API_KEY=sk-xxx python tests/ai/test_deepseek_native_support.py")
