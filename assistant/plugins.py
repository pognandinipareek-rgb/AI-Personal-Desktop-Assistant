import importlib.util
from pathlib import Path
from types import ModuleType


PLUGINS_DIR = Path("plugins")


def load_plugins() -> list[ModuleType]:
    PLUGINS_DIR.mkdir(exist_ok=True)
    modules = []
    for file in PLUGINS_DIR.glob("*.py"):
        if file.name.startswith("_"):
            continue
        spec = importlib.util.spec_from_file_location(f"assistant_plugin_{file.stem}", file)
        if not spec or not spec.loader:
            continue
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        modules.append(module)
    return modules


def handle_with_plugins(command: str) -> str | None:
    for module in load_plugins():
        handler = getattr(module, "handle", None)
        if not callable(handler):
            continue
        result = handler(command)
        if result:
            return str(result)
    return None
