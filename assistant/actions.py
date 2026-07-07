import os
import subprocess
import sys
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus, urlencode

import requests


NOTES_DIR = Path("notes")
SCREENSHOTS_DIR = Path("screenshots")
DOCUMENTS_DIR = Path("documents")

WEBSITE_SHORTCUTS = {
    "amazon": "https://www.amazon.in",
    "chatgpt": "https://chatgpt.com",
    "gmail": "https://mail.google.com",
    "github": "https://github.com",
    "google": "https://www.google.com",
    "linkedin": "https://www.linkedin.com",
    "whatsapp": "https://web.whatsapp.com",
    "whatsapp web": "https://web.whatsapp.com",
    "youtube": "https://www.youtube.com",
}

APP_SHORTCUTS = {
    "calculator": "calc.exe",
    "cmd": "cmd.exe",
    "command prompt": "cmd.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "notepad": "notepad.exe",
    "paint": "mspaint.exe",
    "powershell": "powershell.exe",
    "settings": "ms-settings:",
    "vscode": "code",
    "vs code": "code",
}


def open_chrome() -> str:
    candidates = [
        os.environ.get("CHROME_PATH"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]

    for candidate in candidates:
        if candidate and Path(candidate).exists():
            subprocess.Popen([candidate])
            return "Opening Chrome."

    webbrowser.open("https://www.google.com")
    return "Chrome was not found at the usual paths, so I opened Google in your default browser."


def search_google(query: str) -> str:
    query = query.strip()
    if not query:
        return "What should I search for?"

    webbrowser.open(f"https://www.google.com/search?q={quote_plus(query)}")
    return f"Searching Google for: {query}"


def open_shortcut(name: str) -> str:
    key = name.strip().lower()
    if not key:
        return "Tell me what to open."

    if key in WEBSITE_SHORTCUTS:
        webbrowser.open(WEBSITE_SHORTCUTS[key])
        return f"Opening {key}."

    if key in APP_SHORTCUTS:
        target = APP_SHORTCUTS[key]
        if target.startswith("ms-settings:"):
            os.startfile(target)
        else:
            subprocess.Popen([target], shell=target == "code")
        return f"Opening {key}."

    return f"I do not have a shortcut for {name}. Try open gmail, open youtube, or open notepad."


def search_youtube(query: str) -> str:
    query = query.strip()
    if not query:
        webbrowser.open("https://www.youtube.com")
        return "Opening YouTube."
    webbrowser.open(f"https://www.youtube.com/results?search_query={quote_plus(query)}")
    return f"Searching YouTube for: {query}"


def search_amazon(query: str) -> str:
    query = query.strip()
    if not query:
        webbrowser.open("https://www.amazon.in")
        return "Opening Amazon."
    webbrowser.open(f"https://www.amazon.in/s?k={quote_plus(query)}")
    return f"Searching Amazon for: {query}"


def read_notes() -> str:
    NOTES_DIR.mkdir(exist_ok=True)
    note_files = sorted(
        file for file in NOTES_DIR.glob("*") if file.suffix.lower() in {".txt", ".md"}
    )

    if not note_files:
        sample = NOTES_DIR / "sample_note.txt"
        sample.write_text(
            "This is your notes folder. Add .txt or .md files here and ask me to read my notes.",
            encoding="utf-8",
        )
        return "I created notes/sample_note.txt. Add notes there and ask again."

    parts = []
    for file in note_files[:5]:
        text = file.read_text(encoding="utf-8", errors="replace").strip()
        parts.append(f"{file.name}\n{text[:1200]}")

    return "\n\n---\n\n".join(parts)


def find_files(query: str, root: str | Path = ".") -> str:
    query = query.strip().lower()
    if not query:
        return "Tell me a file name or keyword to search for."

    matches = []
    ignored = {".git", "__pycache__", ".venv", "venv"}
    for path in Path(root).rglob("*"):
        if any(part in ignored for part in path.parts):
            continue
        if path.is_file() and query in path.name.lower():
            matches.append(path)
        if len(matches) >= 10:
            break

    if not matches:
        return f"I could not find a file matching '{query}' in this project folder."
    return "Found files:\n" + "\n".join(str(path) for path in matches)


def open_folder(folder_name: str) -> str:
    key = folder_name.strip().lower()
    folders = {
        "desktop": Path.home() / "Desktop",
        "documents": Path.home() / "Documents",
        "downloads": Path.home() / "Downloads",
        "notes": NOTES_DIR,
        "project": Path.cwd(),
    }
    folder = folders.get(key)
    if not folder:
        return "Try: open folder downloads, open folder desktop, open folder notes."
    folder.mkdir(exist_ok=True)
    os.startfile(folder)
    return f"Opening {key} folder."


def take_screenshot() -> str:
    SCREENSHOTS_DIR.mkdir(exist_ok=True)
    file = SCREENSHOTS_DIR / f"screenshot-{datetime.now().strftime('%Y%m%d-%H%M%S')}.png"
    try:
        from PIL import ImageGrab

        ImageGrab.grab().save(file)
    except Exception as exc:
        return f"Screenshot failed: {exc}"
    return f"Screenshot saved to {file}."


def get_clipboard_text() -> str:
    try:
        import pyperclip

        return pyperclip.paste().strip()
    except Exception:
        return ""


def set_clipboard_text(text: str) -> str:
    try:
        import pyperclip

        pyperclip.copy(text)
        return "Copied the result to clipboard."
    except Exception as exc:
        return f"Clipboard copy failed: {exc}"


def summarize_text(text: str, max_sentences: int = 3) -> str:
    text = " ".join(text.split())
    if not text:
        return "The clipboard is empty."

    sentences = [item.strip() for item in text.replace("?", ".").replace("!", ".").split(".")]
    sentences = [item for item in sentences if item]
    if not sentences:
        return text[:600]
    return ". ".join(sentences[:max_sentences]) + "."


def draft_gmail(to: str = "", subject: str = "", body: str = "") -> str:
    params = urlencode({"to": to, "su": subject, "body": body})
    webbrowser.open(f"https://mail.google.com/mail/?view=cm&fs=1&{params}")
    return "Opening Gmail compose."


def system_control(action: str) -> str:
    action = action.strip().lower()
    if action == "lock":
        subprocess.Popen(["rundll32.exe", "user32.dll,LockWorkStation"])
        return "Locking the screen."
    if action == "mute":
        _send_volume_key(0xAD)
        return "Toggling mute."
    if action == "volume up":
        _send_volume_key(0xAF)
        return "Turning volume up."
    if action == "volume down":
        _send_volume_key(0xAE)
        return "Turning volume down."
    return "Supported system controls: lock screen, mute sound, volume up, volume down."


def _send_volume_key(key_code: int) -> None:
    if sys.platform != "win32":
        return
    import ctypes

    ctypes.windll.user32.keybd_event(key_code, 0, 0, 0)
    ctypes.windll.user32.keybd_event(key_code, 0, 2, 0)


def read_document() -> str:
    DOCUMENTS_DIR.mkdir(exist_ok=True)
    files = sorted(DOCUMENTS_DIR.glob("*.txt")) + sorted(DOCUMENTS_DIR.glob("*.md"))
    pdfs = sorted(DOCUMENTS_DIR.glob("*.pdf"))
    if not files and not pdfs:
        return "Add .txt, .md, or .pdf files to the documents folder, then ask me to read my document."

    if pdfs:
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(pdfs[0]))
            text = "\n".join(page.extract_text() or "" for page in reader.pages[:3])
            return f"{pdfs[0].name}\n{summarize_text(text, 5)}"
        except Exception as exc:
            return f"Could not read PDF: {exc}"

    file = files[0]
    text = file.read_text(encoding="utf-8", errors="replace")
    return f"{file.name}\n{summarize_text(text, 5)}"


def get_weather(city: str) -> str:
    city = city.strip() or "Mumbai"
    geo_response = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city, "count": 1, "language": "en", "format": "json"},
        timeout=10,
    )
    geo_response.raise_for_status()
    matches = geo_response.json().get("results") or []
    if not matches:
        return f"I could not find weather for {city}."

    place = matches[0]
    weather_response = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m",
        },
        timeout=10,
    )
    weather_response.raise_for_status()
    current = weather_response.json()["current"]

    name = place.get("name", city)
    country = place.get("country", "")
    return (
        f"Weather in {name}, {country}: "
        f"{current['temperature_2m']} C, "
        f"{current['relative_humidity_2m']}% humidity, "
        f"wind {current['wind_speed_10m']} km/h."
    )
