import queue
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from assistant.commands import CommandRouter
from assistant import settings
from assistant.speech import speak


class AssistantApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Nova - AI Desktop Assistant")
        self.root.geometry("760x560")
        self.root.minsize(860, 560)

        self.events: queue.Queue[str] = queue.Queue()
        self.router = CommandRouter(self.events)
        self.settings = settings.load_settings()
        self.speak_replies = tk.BooleanVar(value=bool(self.settings["voice_replies"]))
        self.demo_mode = tk.BooleanVar(value=bool(self.settings["demo_mode"]))
        self.use_ollama = tk.BooleanVar(value=bool(self.settings["use_ollama"]))
        self.status_var = tk.StringVar(value="Ready")

        self._configure_style()
        self._build_ui()
        self._poll_events()

    def run(self) -> None:
        self.root.mainloop()

    def _build_ui(self) -> None:
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(1, weight=1)

        sidebar = ttk.Frame(self.root, padding=(14, 14))
        sidebar.grid(row=0, column=0, rowspan=3, sticky="ns")

        ttk.Label(sidebar, text="Quick Actions", font=("Segoe UI", 12, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 8)
        )
        quick_commands = [
            ("Weather", "weather"),
            ("Chrome", "open chrome"),
            ("Gmail", "open gmail"),
            ("YouTube", "open youtube"),
            ("Notes", "read my notes"),
            ("Reminder", "set reminder in 5 minutes drink water"),
            ("Screenshot", "take screenshot"),
            ("History", "show history"),
            ("Memory", "what do you remember"),
            ("Help", "help"),
        ]
        for index, (label, command) in enumerate(quick_commands, start=1):
            button = ttk.Button(
                sidebar,
                text=label,
                command=lambda value=command: self._run_quick_command(value),
            )
            button.grid(row=index, column=0, sticky="ew", pady=3)

        header = ttk.Frame(self.root, padding=(16, 14, 16, 8))
        header.grid(row=0, column=1, sticky="ew")
        header.columnconfigure(0, weight=1)

        title = ttk.Label(header, text="Nova", font=("Segoe UI", 20, "bold"))
        title.grid(row=0, column=0, sticky="w")

        subtitle = ttk.Label(
            header,
            text=f"Default city: {self.settings['default_city']} | Ollama: {self.settings['ollama_model']}",
        )
        subtitle.grid(row=1, column=0, sticky="w", pady=(2, 0))

        self.listen_button = ttk.Button(header, text="Speak", command=self._listen)
        self.listen_button.grid(row=0, column=1, rowspan=2, padx=(8, 0))

        self.speech_toggle = ttk.Checkbutton(
            header,
            text="Voice replies",
            variable=self.speak_replies,
            command=self._save_ui_settings,
        )
        self.speech_toggle.grid(row=0, column=2, rowspan=2, padx=(8, 0))

        settings_button = ttk.Button(header, text="Settings", command=self._open_settings)
        settings_button.grid(row=0, column=3, rowspan=2, padx=(8, 0))

        self.output = scrolledtext.ScrolledText(
            self.root,
            wrap=tk.WORD,
            font=("Consolas", 11),
            padx=12,
            pady=12,
            state=tk.DISABLED,
            background="#f8fafc",
            foreground="#0f172a",
            insertbackground="#0f172a",
        )
        self.output.grid(row=1, column=1, sticky="nsew", padx=16, pady=(4, 8))

        command_bar = ttk.Frame(self.root, padding=(16, 0, 16, 16))
        command_bar.grid(row=2, column=1, sticky="ew")
        command_bar.columnconfigure(0, weight=1)

        self.command_var = tk.StringVar()
        self.command_entry = ttk.Entry(command_bar, textvariable=self.command_var)
        self.command_entry.grid(row=0, column=0, sticky="ew")
        self.command_entry.bind("<Return>", lambda _event: self._submit())
        self.command_entry.focus()

        send_button = ttk.Button(command_bar, text="Send", command=self._submit)
        send_button.grid(row=0, column=1, padx=(8, 0))

        status = ttk.Label(command_bar, textvariable=self.status_var)
        status.grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))

        self._append(
            "Nova is ready.\n"
            "Try: open chrome, open gmail, weather in Mumbai, search youtube Python, "
            "show reminders, demo mode on, settings, help"
        )

    def _configure_style(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#eef2f7")
        style.configure("TLabel", background="#eef2f7", foreground="#0f172a")
        style.configure("TButton", padding=(10, 6))
        style.configure("TCheckbutton", background="#eef2f7", foreground="#0f172a")

    def _submit(self) -> None:
        command = self.command_var.get().strip()
        if not command:
            return

        self.command_var.set("")
        self._append(f"\nYou: {command}")
        self.status_var.set("Working...")
        threading.Thread(target=self._handle_command, args=(command,), daemon=True).start()

    def _run_quick_command(self, command: str) -> None:
        self.command_var.set(command)
        self._submit()

    def _handle_command(self, command: str) -> None:
        try:
            response = self.router.handle(command)
        except Exception as exc:
            response = f"Something went wrong: {exc}"
        self.events.put(f"Assistant: {response}")
        self.events.put("__READY__")
        if self.speak_replies.get():
            speak(response)

    def _listen(self) -> None:
        self.listen_button.configure(state=tk.DISABLED)
        threading.Thread(target=self._listen_worker, daemon=True).start()

    def _listen_worker(self) -> None:
        try:
            import speech_recognition as sr

            recognizer = sr.Recognizer()
            try:
                with sr.Microphone() as source:
                    self.events.put("Listening...")
                    recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    audio = recognizer.listen(source, timeout=6, phrase_time_limit=10)
            except AttributeError as exc:
                if "PyAudio" not in str(exc):
                    raise
                audio = self._record_with_sounddevice(sr)

            text = recognizer.recognize_google(audio)
            self.events.put(f"You: {text}")
            response = self.router.handle(text)
            self.events.put(f"Assistant: {response}")
            self.events.put("__READY__")
            if self.speak_replies.get():
                speak(response)
        except ImportError:
            messagebox.showinfo(
                "Speech unavailable",
                "Install SpeechRecognition and PyAudio to enable microphone input.",
            )
        except Exception as exc:
            self.events.put(f"Speech input failed: {exc}")
        finally:
            self.events.put("__ENABLE_LISTEN__")

    def _record_with_sounddevice(self, sr_module):
        import numpy as np
        import sounddevice as sd

        sample_rate = 16000
        seconds = 6
        self.events.put("Listening with sounddevice...")
        recording = sd.rec(
            int(seconds * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype="int16",
        )
        sd.wait()
        audio_bytes = np.asarray(recording).tobytes()
        return sr_module.AudioData(audio_bytes, sample_rate, 2)

    def _poll_events(self) -> None:
        while True:
            try:
                message = self.events.get_nowait()
            except queue.Empty:
                break

            if message == "__ENABLE_LISTEN__":
                self.listen_button.configure(state=tk.NORMAL)
            elif message == "__READY__":
                self.status_var.set("Ready")
            else:
                self._append(message)

        self.root.after(150, self._poll_events)

    def _save_ui_settings(self) -> None:
        current = settings.load_settings()
        current["voice_replies"] = self.speak_replies.get()
        current["demo_mode"] = self.demo_mode.get()
        settings.save_settings(current)

    def _open_settings(self) -> None:
        window = tk.Toplevel(self.root)
        window.title("Assistant Settings")
        window.geometry("380x260")
        window.resizable(False, False)

        current = settings.load_settings()
        city_var = tk.StringVar(value=current["default_city"])
        model_var = tk.StringVar(value=current["model"])
        demo_var = tk.BooleanVar(value=current["demo_mode"])
        voice_var = tk.BooleanVar(value=current["voice_replies"])
        ollama_var = tk.BooleanVar(value=current["use_ollama"])
        ollama_model_var = tk.StringVar(value=current["ollama_model"])

        frame = ttk.Frame(window, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Default city").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=city_var).grid(row=0, column=1, sticky="ew", pady=6)

        ttk.Label(frame, text="OpenAI model").grid(row=1, column=0, sticky="w")
        ttk.Entry(frame, textvariable=model_var).grid(row=1, column=1, sticky="ew", pady=6)

        ttk.Checkbutton(frame, text="Demo mode", variable=demo_var).grid(
            row=2, column=0, columnspan=2, sticky="w", pady=6
        )
        ttk.Checkbutton(frame, text="Voice replies", variable=voice_var).grid(
            row=3, column=0, columnspan=2, sticky="w", pady=6
        )
        ttk.Checkbutton(frame, text="Use Ollama local AI", variable=ollama_var).grid(
            row=4, column=0, columnspan=2, sticky="w", pady=6
        )

        ttk.Label(frame, text="Ollama model").grid(row=5, column=0, sticky="w")
        ttk.Entry(frame, textvariable=ollama_model_var).grid(row=5, column=1, sticky="ew", pady=6)

        frame.columnconfigure(1, weight=1)

        def save() -> None:
            new_settings = settings.load_settings()
            new_settings["default_city"] = city_var.get().strip() or "Mumbai"
            new_settings["model"] = model_var.get().strip() or "gpt-4o-mini"
            new_settings["demo_mode"] = demo_var.get()
            new_settings["voice_replies"] = voice_var.get()
            new_settings["use_ollama"] = ollama_var.get()
            new_settings["ollama_model"] = ollama_model_var.get().strip() or "qwen2.5-coder:1.5b"
            settings.save_settings(new_settings)
            self.settings = new_settings
            self.speak_replies.set(voice_var.get())
            self.demo_mode.set(demo_var.get())
            self.use_ollama.set(ollama_var.get())
            self._append("Assistant: Settings saved.")
            window.destroy()

        ttk.Button(frame, text="Save", command=save).grid(row=6, column=1, sticky="e", pady=(16, 0))

    def _append(self, text: str) -> None:
        self.output.configure(state=tk.NORMAL)
        self.output.insert(tk.END, text + "\n")
        self.output.configure(state=tk.DISABLED)
        self.output.see(tk.END)
