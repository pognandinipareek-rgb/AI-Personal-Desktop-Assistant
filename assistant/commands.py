import os
import queue
import re
from datetime import datetime

from assistant import actions, history, memory, reminders, settings
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

        if normalized in {"nova stop", "stop", "stop speaking", "quiet"}:
            return "STOP_SPEECH"

        if normalized in {"show history", "read history", "conversation history"}:
            return history.read_history()

        if normalized in {"show settings", "settings"}:
            return self._show_settings()

        if normalized.startswith("set default city "):
            city = command[len("set default city ") :].strip()
            return settings.set_value("default_city", city or "Mumbai")

        if normalized in {"demo mode on", "enable demo mode"}:
            return settings.set_value("demo_mode", True)

        if normalized in {"demo mode off", "disable demo mode"}:
            return settings.set_value("demo_mode", False)

        if normalized in {"ollama on", "enable ollama"}:
            return settings.set_value("use_ollama", True)

        if normalized in {"ollama off", "disable ollama"}:
            return settings.set_value("use_ollama", False)

        if normalized.startswith("set ollama model "):
            model = command[len("set ollama model ") :].strip()
            return settings.set_value("ollama_model", model or "qwen2.5-coder:1.5b")

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
            if not city:
                city = settings.load_settings()["default_city"]
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

        if normalized in {"show reminders", "list reminders"}:
            return reminders.list_reminders()

        if normalized.startswith("cancel reminder "):
            return self._cancel_reminder(command)

        if normalized in {"clear reminders", "cancel all reminders"}:
            return reminders.clear_reminders()

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
        return ask_llm(command, demo_mode=settings.load_settings()["demo_mode"])

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

        reminder = reminders.add_reminder(seconds, message, self.events.put)
        return f"Reminder {reminder.id} set for {reminder.due_at.strftime('%I:%M %p')}: {message}"

    def _cancel_reminder(self, command: str) -> str:
        match = re.search(r"cancel reminder\s+(\d+)", command, flags=re.IGNORECASE)
        if not match:
            return "Use: cancel reminder 2"
        return reminders.cancel_reminder(int(match.group(1)))

    def _study_from_notes(self, instruction: str) -> str:
        notes = actions.read_notes()
        if notes.startswith("I created"):
            return notes
        return ask_llm(f"{instruction}:\n\n{notes}", demo_mode=settings.load_settings()["demo_mode"])

    def _daily_greeting(self) -> str:
        hour = datetime.now().hour
        greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"
        return (
            f"{greeting}. Today is {datetime.now().strftime('%A, %d %B %Y')}. "
            f"Your default weather city is {settings.load_settings()['default_city']}. "
            "Try weather, read my notes, or start a reminder."
        )

    def _show_settings(self) -> str:
        current = settings.load_settings()
        return (
            "Settings:\n"
            f"default_city: {current['default_city']}\n"
            f"voice_replies: {current['voice_replies']}\n"
            f"demo_mode: {current['demo_mode']}\n"
            f"model: {current['model']}\n"
            f"use_ollama: {current['use_ollama']}\n"
            f"ollama_model: {current['ollama_model']}\n"
            f"theme: {current['theme']}"
        )

    def _extract_after(self, command: str, markers: list[str]) -> str:
        lowered = command.lower()
        for marker in markers:
            index = lowered.find(marker)
            if index >= 0:
                return command[index + len(marker) :].strip(" :,-")
        return ""

    def _help(self) -> str:
        current = settings.load_settings()
        llm_status = "enabled" if os.environ.get("OPENAI_API_KEY") else "not configured"
        return (
            "Commands: open chrome/gmail/youtube/notepad, weather in <city>, "
            "search google <query>, search youtube <query>, search amazon <query>, "
            "read my notes, read my document, find file <name>, open folder downloads, "
            "set reminder in <number> minutes <message>, show reminders, cancel reminder <id>, "
            "take screenshot, summarize clipboard, "
            "rewrite clipboard, translate clipboard to Hindi, draft email <message>, remember <fact>, "
            "what do you remember, quiz me, make flashcards, settings, demo mode on/off. "
            f"LLM is {llm_status}. Ollama is {current['use_ollama']}. Demo mode is {current['demo_mode']}."
        )
