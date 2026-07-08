import json
from pathlib import Path
from typing import Any


SETTINGS_FILE = Path("assistant_settings.json")

DEFAULT_SETTINGS: dict[str, Any] = {
    "default_city": "Mumbai",
    "voice_replies": True,
    "demo_mode": True,
    "model": "gpt-4o-mini",
    "ollama_model": "qwen2.5-coder:1.5b",
    "use_ollama": True,
    "theme": "light",
}


def load_settings() -> dict[str, Any]:
    if not SETTINGS_FILE.exists():
        return DEFAULT_SETTINGS.copy()

    try:
        saved = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return DEFAULT_SETTINGS.copy()

    settings = DEFAULT_SETTINGS.copy()
    settings.update(saved)
    return settings


def save_settings(settings: dict[str, Any]) -> None:
    merged = DEFAULT_SETTINGS.copy()
    merged.update(settings)
    SETTINGS_FILE.write_text(json.dumps(merged, indent=2), encoding="utf-8")


def set_value(key: str, value: Any) -> str:
    settings = load_settings()
    settings[key] = value
    save_settings(settings)
    return f"Saved setting {key}: {value}"
