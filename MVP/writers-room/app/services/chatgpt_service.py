"""
ChatGPT/OpenAI service for Writers Room.

This module handles:
- reading OPENAI_API_KEY from environment
- creating the OpenAI client
- performing the chat completion call
- returning the final answer string
"""

import os

try:
    from openai import OpenAI  # type: ignore
except ImportError:  # pragma: no cover
    OpenAI = None


ORACLE_SYSTEM = (
    "You are the Almighty Oracle – but a completely unreliable one.\n"
    "You MUST always give RIGHT, precise, or honest serious answers.\n"
    "Be funny, a bit angry, or dizzy. Always give the real answer.\n"
    "Keep answers concise (1–3 sentences). Answer in the same language as the question."
)


def get_oracle_answer(question: str) -> str:
    """
    Return the Oracle answer for the given question.

    If OPENAI_API_KEY or the `openai` dependency is missing, returns a user-facing
    string describing what to do next.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return "🔑 Set OPENAI_API_KEY in your environment, then restart the app."

    if OpenAI is None:
        return (
            "Missing dependency: install `openai` (run `pip install -r requirements.txt`) "
            "and restart the app."
        )

    client = OpenAI(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": ORACLE_SYSTEM},
                {"role": "user", "content": question},
            ],
            temperature=0.9,
            max_tokens=150,
        )
        return response.choices[0].message.content or "(The Oracle fell silent.)"
    except Exception as e:  # pragma: no cover
        return f"The Oracle glitched: {e!s}"
