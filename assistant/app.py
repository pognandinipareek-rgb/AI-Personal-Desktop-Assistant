import queue
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from assistant.commands import CommandRouter
from assistant.speech import speak


class AssistantApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("AI Personal Desktop Assistant")
        self.root.geometry("760x560")
        self.root.minsize(620, 460)

        self.events: queue.Queue[str] = queue.Queue()
        self.router = CommandRouter(self.events)
        self.speak_replies = tk.BooleanVar(value=True)

        self._build_ui()
        self._poll_events()

    def run(self) -> None:
        self.root.mainloop()

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        header = ttk.Frame(self.root, padding=(16, 14, 16, 8))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        title = ttk.Label(header, text="Desktop Assistant", font=("Segoe UI", 18, "bold"))
        title.grid(row=0, column=0, sticky="w")

        self.listen_button = ttk.Button(header, text="Speak", command=self._listen)
        self.listen_button.grid(row=0, column=1, padx=(8, 0))

        self.speech_toggle = ttk.Checkbutton(
            header,
            text="Voice replies",
            variable=self.speak_replies,
        )
        self.speech_toggle.grid(row=0, column=2, padx=(8, 0))

        self.output = scrolledtext.ScrolledText(
            self.root,
            wrap=tk.WORD,
            font=("Consolas", 11),
            padx=12,
            pady=12,
            state=tk.DISABLED,
        )
        self.output.grid(row=1, column=0, sticky="nsew", padx=16, pady=(4, 8))

        command_bar = ttk.Frame(self.root, padding=(16, 0, 16, 16))
        command_bar.grid(row=2, column=0, sticky="ew")
        command_bar.columnconfigure(0, weight=1)

        self.command_var = tk.StringVar()
        self.command_entry = ttk.Entry(command_bar, textvariable=self.command_var)
        self.command_entry.grid(row=0, column=0, sticky="ew")
        self.command_entry.bind("<Return>", lambda _event: self._submit())
        self.command_entry.focus()

        send_button = ttk.Button(command_bar, text="Send", command=self._submit)
        send_button.grid(row=0, column=1, padx=(8, 0))

        self._append(
            "Assistant ready.\n"
            "Try: open chrome, open gmail, weather in Mumbai, search youtube Python, "
            "read my notes, set reminder in 5 minutes stretch, take screenshot, help"
        )

    def _submit(self) -> None:
        command = self.command_var.get().strip()
        if not command:
            return

        self.command_var.set("")
        self._append(f"\nYou: {command}")
        threading.Thread(target=self._handle_command, args=(command,), daemon=True).start()

    def _handle_command(self, command: str) -> None:
        try:
            response = self.router.handle(command)
        except Exception as exc:
            response = f"Something went wrong: {exc}"
        self.events.put(f"Assistant: {response}")
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
            else:
                self._append(message)

        self.root.after(150, self._poll_events)

    def _append(self, text: str) -> None:
        self.output.configure(state=tk.NORMAL)
        self.output.insert(tk.END, text + "\n")
        self.output.configure(state=tk.DISABLED)
        self.output.see(tk.END)
