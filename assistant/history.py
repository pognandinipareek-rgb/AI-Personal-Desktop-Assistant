from datetime import datetime
from pathlib import Path


HISTORY_FILE = Path("assistant_history.txt")


def log_exchange(command: str, response: str) -> None:
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with HISTORY_FILE.open("a", encoding="utf-8") as file:
        file.write(f"[{stamp}] You: {command}\n")
        file.write(f"[{stamp}] Assistant: {response}\n\n")


def read_history(limit: int = 20) -> str:
    if not HISTORY_FILE.exists():
        return "No history yet."

    blocks = HISTORY_FILE.read_text(encoding="utf-8", errors="replace").strip().split("\n\n")
    return "\n\n".join(blocks[-limit:]) if blocks else "No history yet."
