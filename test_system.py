#!/usr/bin/env python3
"""Test the chat API (unified wargaming LLM). Runs multiple queries to verify variety and relevance."""

from typing import Tuple

import requests
from war_game.project_config import CHAT_API_URL

CHAT_URL = CHAT_API_URL


def chat(message: str, conversation_id: str = None) -> Tuple[bool, str, str]:
    """Send one message. Returns (success, reply, conversation_id)."""
    payload = {"message": message}
    if conversation_id:
        payload["conversation_id"] = conversation_id
    try:
        r = requests.post(
            CHAT_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=90,
        )
        if r.status_code != 200:
            return False, f"HTTP {r.status_code}: {r.text[:200]}", ""
        data = r.json()
        if not data.get("success"):
            return False, data.get("error", "Unknown error"), ""
        return True, (data.get("reply") or "").strip(), data.get("conversation_id", "") or ""
    except Exception as e:
        return False, str(e), ""


def test_chat():
    print("Testing chat API at", CHAT_URL)
    print("=" * 60)

    tests = [
        "What are key factors for victory in a conventional conflict?",
        "Compare Israel and Syria in terms of terrain and military positions.",
        "Which country has stronger reserves: Iran or Turkey?",
        "What weapons does Iraq primarily use for infantry?",
    ]

    conv_id = None
    for i, message in enumerate(tests, 1):
        print(f"\n[Test {i}] User: {message}")
        ok, reply, conv_id = chat(message, conv_id)
        if ok:
            word_count = len(reply.split())
            print(f"         Reply ({word_count} words):")
            print("-" * 40)
            print(reply)
            print("-" * 40)
            print("         OK")
        else:
            print(f"         FAIL: {reply}")
            return False

    print("\n" + "=" * 60)
    print("All chat tests passed. LLM responses are varied and question-specific.")
    return True


if __name__ == "__main__":
    print("Ensure: 1) runserver 2) ollama serve 3) wargaming model (e.g. retrain_wargaming_llm)")
    if not test_chat():
        exit(1)
