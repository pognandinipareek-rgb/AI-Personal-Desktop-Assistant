import os
from pathlib import Path


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


def ask_llm(prompt: str) -> str:
    _load_local_env()

    if not prompt:
        return "What would you like to ask?"

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return (
            "I can handle desktop commands now. To enable general AI answers, "
            "set OPENAI_API_KEY and try again."
        )

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        system_prompt = "You are a concise personal desktop assistant. When asked for code, provide runnable examples."

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
        if status:
            return f"LLM request failed ({status}): {message}\n{body or ''}".strip()
        return f"LLM request failed: {message}"
