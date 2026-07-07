import os
import queue
import re
import threading
from datetime import datetime, timedelta

from assistant import actions, history, memory
from assistant.llm import ask_llm
from assistant.plugins import handle_with_plugins


class CommandRouter:
    def __init__(self, events: queue.Queue[str]) -> None:
        self.events = events

    def handle(self, command: str) -> str:
        response = self._handle(command)
        history.log_exchange(command, response)
        return response

    def _handle(self, command: str) -> str:
        normalized = command.strip().lower()
        normalized = re.sub(r"^(hey assistant|assistant)[, ]+", "", normalized)

        if normalized in {"help", "commands"}:
            return self._help()

        plugin_response = handle_with_plugins(command)
        if plugin_response:
            return plugin_response

        if normalized in {"good morning", "good afternoon", "good evening", "start my day"}:
            return self._daily_greeting()

        if normalized in {"show history", "read history", "conversation history"}:
            return history.read_history()

        if normalized.startswith("remember "):
            return memory.remember(command.split(" ", 1)[1])

        if normalized in {"what do you remember", "show memory", "recall memory"}:
            return memory.recall()

        if normalized == "forget everything":
            return memory.forget_all()

        if "open chrome" in normalized:
            return actions.open_chrome()

        if normalized.startswith("open folder "):
            return actions.open_folder(command[len("open folder ") :])

        if normalized.startswith("open "):
            return actions.open_shortcut(command[len("open ") :])

        if normalized.startswith("search google"):
            return actions.search_google(command[len("search google") :])

        if normalized.startswith("google "):
            return actions.search_google(command[len("google ") :])

        if normalized.startswith("search youtube"):
            return actions.search_youtube(command[len("search youtube") :])

        if "youtube" in normalized and "search" in normalized:
            query = self._extract_after(command, ["search youtube for", "youtube search", "search youtube"])
            return actions.search_youtube(query)

        if normalized.startswith("search amazon"):
            return actions.search_amazon(command[len("search amazon") :])

        if "amazon" in normalized and "search" in normalized:
            query = self._extract_after(command, ["search amazon for", "amazon search", "search amazon"])
            return actions.search_amazon(query)

        if "weather" in normalized:
            city = self._extract_after(command, ["weather in", "weather for", "weather"])
            return actions.get_weather(city)

        if "read my notes" in normalized or normalized == "read notes":
            return actions.read_notes()

        if normalized in {"read my document", "read document", "summarize document", "read my pdf"}:
            return actions.read_document()

        if normalized.startswith("find file "):
            return actions.find_files(command[len("find file ") :])

        if normalized.startswith("find "):
            return actions.find_files(command[len("find ") :])

        if normalized.startswith("set reminder") or normalized.startswith("remind me"):
            return self._set_reminder(command)

        if normalized in {"take screenshot", "screenshot"}:
            return actions.take_screenshot()

        if normalized in {"lock screen", "lock my screen"}:
            return actions.system_control("lock")

        if normalized in {"mute", "mute sound"}:
            return actions.system_control("mute")

        if normalized in {"volume up", "increase volume"}:
            return actions.system_control("volume up")

        if normalized in {"volume down", "decrease volume"}:
            return actions.system_control("volume down")

        if normalized in {"summarize clipboard", "summary of clipboard"}:
            return actions.summarize_text(actions.get_clipboard_text())

        if normalized in {"rewrite clipboard", "rewrite clipboard professionally"}:
            text = actions.get_clipboard_text()
            if not text:
                return "The clipboard is empty."
            result = ask_llm(f"Rewrite this professionally:\n\n{text}")
            copy_status = actions.set_clipboard_text(result)
            return f"{result}\n\n{copy_status}"

        if normalized.startswith("translate clipboard"):
            text = actions.get_clipboard_text()
            if not text:
                return "The clipboard is empty."
            language = self._extract_after(command, ["translate clipboard to", "translate clipboard"]) or "Hindi"
            result = ask_llm(f"Translate this to {language}:\n\n{text}")
            copy_status = actions.set_clipboard_text(result)
            return f"{result}\n\n{copy_status}"

        if normalized.startswith("draft email"):
            body = command[len("draft email") :].strip(" :-")
            return actions.draft_gmail(subject="Draft from assistant", body=body)

        if normalized.startswith("quiz me"):
            return self._study_from_notes("Create 5 quiz questions from these notes")

        if normalized.startswith("make flashcards"):
            return self._study_from_notes("Create concise flashcards from these notes")

        if normalized.startswith("ask "):
            return ask_llm(command[4:].strip())

        return self._smart_fallback(command)

    def _smart_fallback(self, command: str) -> str:
        lowered = command.lower()
        if "remind" in lowered:
            return self._set_reminder(command)
        if "search" in lowered:
            query = self._extract_after(command, ["search for", "search"])
            return actions.search_google(query)
        return ask_llm(command)

    def _set_reminder(self, command: str) -> str:
        patterns = [
            r"in\s+(\d+)\s+(second|seconds|minute|minutes|hour|hours)\s+(.+)",
            r"after\s+(\d+)\s+(second|seconds|minute|minutes|hour|hours)\s+(.+)",
        ]
        match = None
        for pattern in patterns:
            match = re.search(pattern, command, flags=re.IGNORECASE)
            if match:
                break

        if not match:
            return "Use: set reminder in 10 minutes drink water"

        amount = int(match.group(1))
        unit = match.group(2).lower()
        message = match.group(3).strip()
        message = re.sub(r"^(to|for)\s+", "", message, flags=re.IGNORECASE)

        seconds = amount
        if unit.startswith("minute"):
            seconds = amount * 60
        elif unit.startswith("hour"):
            seconds = amount * 60 * 60

        due_at = datetime.now() + timedelta(seconds=seconds)
        threading.Timer(seconds, lambda: self.events.put(f"Reminder: {message}")).start()
        return f"Reminder set for {due_at.strftime('%I:%M %p')}: {message}"

    def _study_from_notes(self, instruction: str) -> str:
        notes = actions.read_notes()
        if notes.startswith("I created"):
            return notes
        return ask_llm(f"{instruction}:\n\n{notes}")

    def _daily_greeting(self) -> str:
        hour = datetime.now().hour
        greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"
        return (
            f"{greeting}. Today is {datetime.now().strftime('%A, %d %B %Y')}. "
            "Try weather in Mumbai, read my notes, or start a reminder."
        )

    def _extract_after(self, command: str, markers: list[str]) -> str:
        lowered = command.lower()
        for marker in markers:
            index = lowered.find(marker)
            if index >= 0:
                return command[index + len(marker) :].strip(" :,-")
        return ""

    def _help(self) -> str:
        llm_status = "enabled" if os.environ.get("OPENAI_API_KEY") else "not configured"
        return (
            "Commands: open chrome/gmail/youtube/notepad, weather in <city>, "
            "search google <query>, search youtube <query>, search amazon <query>, "
            "read my notes, read my document, find file <name>, open folder downloads, "
            "set reminder in <number> minutes <message>, take screenshot, summarize clipboard, "
            "rewrite clipboard, translate clipboard to Hindi, draft email <message>, remember <fact>, "
            f"what do you remember, quiz me, make flashcards. LLM is {llm_status}."
        )
