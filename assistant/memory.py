import json
from pathlib import Path


MEMORY_FILE = Path("assistant_memory.json")


def _load() -> dict[str, str]:
    if not MEMORY_FILE.exists():
        return {}
    try:
        return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def remember(text: str) -> str:
    text = text.strip()
    if not text:
        return "Tell me what to remember."

    memory = _load()
    key = f"memory_{len(memory) + 1}"
    memory[key] = text
    MEMORY_FILE.write_text(json.dumps(memory, indent=2), encoding="utf-8")
    return f"I will remember: {text}"


def recall() -> str:
    memory = _load()
    if not memory:
        return "I do not have any saved memories yet."
    return "Saved memories:\n" + "\n".join(f"- {value}" for value in memory.values())


def forget_all() -> str:
    MEMORY_FILE.write_text("{}", encoding="utf-8")
    return "I cleared my saved memories."
