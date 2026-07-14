import os
from pathlib import Path

import requests

from assistant import settings


def _load_local_env() -> None:
    env_file = Path(".env")
    if not env_file.exists():
        return

    for line in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ[key] = value


def ask_llm(prompt: str, demo_mode: bool = True) -> str:
    _load_local_env()

    if not prompt:
        return "What would you like to ask?"

    current_settings = settings.load_settings()

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        ollama_answer = _ask_ollama(prompt, current_settings)
        if ollama_answer:
            return ollama_answer
        if demo_mode:
            return _demo_answer(prompt, "No API key is configured yet.")
        return (
            "I can handle desktop commands now. To enable general AI answers, "
            "set OPENAI_API_KEY and try again."
        )

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key, timeout=12)
        model = os.environ.get("OPENAI_MODEL") or current_settings["model"]
        system_prompt = "You are Nova, a concise personal desktop assistant. When asked for code, provide runnable examples."

        try:
            response = client.responses.create(
                model=model,
                instructions=system_prompt,
                input=prompt,
            )
            return response.output_text or "I did not get a response."
        except Exception:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
            )
            return response.choices[0].message.content or "I did not get a response."
    except Exception as exc:
        status = getattr(exc, "status_code", None)
        body = getattr(exc, "body", None)
        message = getattr(exc, "message", str(exc))
        ollama_answer = _ask_ollama(prompt, current_settings)
        if ollama_answer:
            return ollama_answer
        if demo_mode and ("insufficient_quota" in str(body) or status in {400, 401, 429}):
            return _demo_answer(prompt, f"OpenAI API is unavailable right now: {message}")
        if status:
            return f"LLM request failed ({status}): {message}\n{body or ''}".strip()
        return f"LLM request failed: {message}"


def _ask_ollama(prompt: str, current_settings: dict) -> str | None:
    if not current_settings.get("use_ollama", True):
        return None

    model = current_settings.get("ollama_model", "qwen2.5-coder:1.5b")
    try:
        response = requests.post(
            "http://127.0.0.1:11434/api/generate",
            json={
                "model": model,
                "prompt": (
                    "You are Nova, a concise personal desktop assistant. "
                    "When asked for code, provide runnable examples.\n\n"
                    f"User: {prompt}"
                ),
                "stream": False,
            },
            timeout=45,
        )
        response.raise_for_status()
        data = response.json()
        text = (data.get("response") or "").strip()
        if text:
            return f"Ollama local AI ({model}):\n\n{text}"
    except Exception:
        return None
    return None


def _demo_answer(prompt: str, reason: str) -> str:
    lowered = prompt.lower()
    if "recursion" in lowered and "code" in lowered:
        return (
            f"Demo mode answer ({reason})\n\n"
            "Here is a simple Python recursion example:\n\n"
            "```python\n"
            "def factorial(n):\n"
            "    if n <= 1:\n"
            "        return 1\n"
            "    return n * factorial(n - 1)\n\n"
            "print(factorial(5))  # 120\n"
            "```"
        )

    if "email" in lowered:
        return (
            f"Demo mode answer ({reason})\n\n"
            "Subject: Quick Update\n\n"
            "Hello,\n\n"
            "I wanted to share a quick update regarding this. Please let me know if you need "
            "any more details.\n\n"
            "Thank you."
        )

    if "flashcard" in lowered or "quiz" in lowered:
        return (
            f"Demo mode answer ({reason})\n\n"
            "1. Q: What is recursion? A: A function calling itself with a smaller problem.\n"
            "2. Q: What stops recursion? A: A base case.\n"
            "3. Q: What happens without a base case? A: The function can run until a recursion error."
        )

    return (
        f"Demo mode answer ({reason})\n\n"
        "I can answer this fully once API billing/quota is active. For now, I can still run "
        "desktop commands like weather, reminders, screenshots, notes, search, and app shortcuts."
    )
