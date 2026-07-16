import queue
import threading
import tkinter as tk
from tkinter import scrolledtext, ttk

from .commands import CommandRouter
from . import settings
from .speech import speak


class AssistantApp:
    COLORS = {
        "bg": "#f4f7fb",
        "panel": "#ffffff",
        "panel_alt": "#eef4ff",
        "border": "#d9e2ef",
        "text": "#182230",
        "muted": "#667085",
        "primary": "#2563eb",
        "primary_hover": "#1d4ed8",
        "success": "#15803d",
        "log_bg": "#0f172a",
        "log_text": "#dbeafe",
        "log_muted": "#93a4b8",
        "user": "#bfdbfe",
        "assistant": "#bbf7d0",
        "error": "#fecaca",
    }

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("AI Personal Desktop Assistant")
        self.root.geometry("880x640")
        self.root.minsize(720, 520)
        self.root.configure(bg=self.COLORS["bg"])

        self.events: queue.Queue[str] = queue.Queue()
        self.router = CommandRouter(self.events)
        self.speak_replies = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="Ready")

        self._configure_styles()
        self._build_ui()
        self._poll_events()

    def run(self) -> None:
        self.root.mainloop()

    def _configure_styles(self) -> None:
        self.style = ttk.Style(self.root)
        self.style.theme_use("clam")
        self.style.configure(".", font=("Segoe UI", 10))
        self.style.configure("App.TFrame", background=self.COLORS["bg"])
        self.style.configure("Panel.TFrame", background=self.COLORS["panel"])
        self.style.configure("Hero.TFrame", background=self.COLORS["panel_alt"])
        self.style.configure(
            "Title.TLabel",
            background=self.COLORS["panel_alt"],
            foreground=self.COLORS["text"],
            font=("Segoe UI", 22, "bold"),
        )
        self.style.configure(
            "Subtitle.TLabel",
            background=self.COLORS["panel_alt"],
            foreground=self.COLORS["muted"],
            font=("Segoe UI", 10),
        )
        self.style.configure(
            "Status.TLabel",
            background=self.COLORS["panel"],
            foreground=self.COLORS["success"],
            font=("Segoe UI", 9, "bold"),
            padding=(10, 4),
        )
        self.style.configure(
            "Primary.TButton",
            background=self.COLORS["primary"],
            foreground="#ffffff",
            borderwidth=0,
            focusthickness=0,
            padding=(16, 9),
            font=("Segoe UI", 10, "bold"),
        )
        self.style.map(
            "Primary.TButton",
            background=[("active", self.COLORS["primary_hover"]), ("disabled", "#9aa8bd")],
            foreground=[("disabled", "#ffffff")],
        )
        self.style.configure(
            "Soft.TButton",
            background="#e7eefb",
            foreground=self.COLORS["text"],
            borderwidth=0,
            padding=(14, 9),
            font=("Segoe UI", 10, "bold"),
        )
        self.style.map("Soft.TButton", background=[("active", "#d7e4f8")])
        self.style.configure(
            "Voice.TCheckbutton",
            background=self.COLORS["panel_alt"],
            foreground=self.COLORS["text"],
            padding=(8, 4),
        )
        self.style.map("Voice.TCheckbutton", background=[("active", self.COLORS["panel_alt"])])
        self.style.configure(
            "Command.TEntry",
            fieldbackground="#ffffff",
            foreground=self.COLORS["text"],
            bordercolor=self.COLORS["border"],
            lightcolor=self.COLORS["border"],
            darkcolor=self.COLORS["border"],
            padding=(12, 10),
        )

    def _build_ui(self) -> None:
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(1, weight=1)

        shell = ttk.Frame(self.root, style="App.TFrame", padding=20)
        shell.grid(row=0, column=0, rowspan=3, sticky="nsew")
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(1, weight=1)

        header = ttk.Frame(shell, style="Hero.TFrame", padding=(22, 18, 22, 18))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        title = ttk.Label(header, text="Desktop Assistant", style="Title.TLabel")
        title.grid(row=0, column=0, sticky="w")

        subtitle = ttk.Label(
            header,
            text="Ask questions, run desktop actions, search, summarize notes, and capture quick reminders.",
            style="Subtitle.TLabel",
        )
        subtitle.grid(row=1, column=0, sticky="w", pady=(4, 0))

        self.speech_toggle = ttk.Checkbutton(
            header,
            text="Voice replies",
            variable=self.speak_replies,
            style="Voice.TCheckbutton",
        )
        self.speech_toggle.grid(row=0, column=1, padx=(14, 0), sticky="e")

        self.listen_button = ttk.Button(header, text="Speak", command=self._listen, style="Primary.TButton")
        self.listen_button.grid(row=0, column=2, padx=(8, 0), rowspan=2, sticky="e")

        content = ttk.Frame(shell, style="Panel.TFrame", padding=(16, 14, 16, 16))
        content.grid(row=1, column=0, sticky="nsew", pady=(14, 12))
        content.columnconfigure(0, weight=1)
        content.rowconfigure(1, weight=1)

        content_header = ttk.Frame(content, style="Panel.TFrame")
        content_header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        content_header.columnconfigure(0, weight=1)

        ttk.Label(
            content_header,
            text="Conversation",
            background=self.COLORS["panel"],
            foreground=self.COLORS["text"],
            font=("Segoe UI", 13, "bold"),
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(content_header, textvariable=self.status_var, style="Status.TLabel").grid(row=0, column=1, sticky="e")

        self.output = scrolledtext.ScrolledText(
            content,
            wrap=tk.WORD,
            font=("Cascadia Mono", 10),
            padx=16,
            pady=14,
            state=tk.DISABLED,
            relief=tk.FLAT,
            borderwidth=0,
            background=self.COLORS["log_bg"],
            foreground=self.COLORS["log_text"],
            insertbackground=self.COLORS["log_text"],
        )
        self.output.grid(row=1, column=0, sticky="nsew")
        self.output.tag_configure("user", foreground=self.COLORS["user"], spacing1=8)
        self.output.tag_configure("assistant", foreground=self.COLORS["assistant"], spacing1=8)
        self.output.tag_configure("system", foreground=self.COLORS["log_muted"], spacing1=4)
        self.output.tag_configure("error", foreground=self.COLORS["error"], spacing1=8)

        command_bar = ttk.Frame(shell, style="Panel.TFrame", padding=(16, 14, 16, 14))
        command_bar.grid(row=2, column=0, sticky="ew")
        command_bar.columnconfigure(0, weight=1)

        self.command_var = tk.StringVar()
        self.command_entry = ttk.Entry(command_bar, textvariable=self.command_var, style="Command.TEntry")
        self.command_entry.grid(row=0, column=0, sticky="ew")
        self.command_entry.bind("<Return>", lambda _event: self._submit())
        self.command_entry.focus()

        send_button = ttk.Button(command_bar, text="Send", command=self._submit, style="Soft.TButton")
        send_button.grid(row=0, column=1, padx=(8, 0))

        status = ttk.Label(command_bar, textvariable=self.status_var)
        status.grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))

        self._append(
            "Nova is ready.\n"
            "Try: open chrome, open gmail, weather in Mumbai, search youtube Python, "
            "read my notes, set reminder in 5 minutes stretch, take screenshot, help",
            "system",
        )

    def _submit(self) -> None:
        command = self.command_var.get().strip()
        if not command:
            return

        self.status_var.set("Thinking")
        self._append(f"You: {command}", "user")
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
        self.status_var.set("Listening")
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
            self.root.after(
                0,
                lambda: self._show_dialog(
                    "Speech unavailable",
                    "Install SpeechRecognition and PyAudio to enable microphone input.",
                    "Microphone support needs a couple of optional packages before this button can listen.",
                ),
            )
        except OSError as exc:
            self.root.after(
                0,
                lambda: self._show_dialog(
                    "Microphone unavailable",
                    "Unable to access the microphone.",
                    f"{exc}",
                ),
            )
        except Exception as exc:
            self.root.after(
                0,
                lambda: self._show_dialog(
                    "Speech input failed",
                    "An error occurred while trying to capture speech.",
                    str(exc),
                ),
            )
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
                self._append_event(message)

        self.root.after(150, self._poll_events)

    def _append_event(self, message: str) -> None:
        if message.startswith("You:"):
            self._append(message, "user")
        elif message.startswith("Assistant:"):
            self.status_var.set("Ready")
            self._append(message, "assistant")
        elif "failed" in message.lower() or "went wrong" in message.lower():
            self.status_var.set("Needs attention")
            self._append(message, "error")
        else:
            self._append(message, "system")

    def _append(self, text: str, tag: str = "system") -> None:
        self.output.configure(state=tk.NORMAL)
        self.output.insert(tk.END, text + "\n\n", tag)
        self.output.configure(state=tk.DISABLED)
        self.output.see(tk.END)

    def _show_dialog(self, title: str, message: str, detail: str = "") -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.transient(self.root)
        dialog.attributes("-topmost", True)
        dialog.grab_set()
        dialog.configure(bg=self.COLORS["bg"])
        dialog.resizable(False, False)

        card = tk.Frame(dialog, bg=self.COLORS["panel"], padx=24, pady=22)
        card.grid(row=0, column=0, sticky="nsew", padx=14, pady=14)
        card.columnconfigure(0, weight=1)

        tk.Label(
            card,
            text=title,
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
            font=("Segoe UI", 17, "bold"),
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            card,
            text=message,
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
            font=("Segoe UI", 10),
            wraplength=420,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(10, 0))

        if detail:
            tk.Label(
                card,
                text=detail,
                bg=self.COLORS["panel"],
                fg=self.COLORS["muted"],
                font=("Segoe UI", 9),
                wraplength=420,
                justify="left",
            ).grid(row=2, column=0, sticky="w", pady=(8, 0))

        close_button = ttk.Button(dialog, text="Got it", command=dialog.destroy, style="Primary.TButton")
        close_button.grid(row=1, column=0, sticky="e", padx=18, pady=(0, 18))

        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        close_button.focus_set()
        dialog.bind("<Return>", lambda _event: dialog.destroy())
        dialog.bind("<Escape>", lambda _event: dialog.destroy())
