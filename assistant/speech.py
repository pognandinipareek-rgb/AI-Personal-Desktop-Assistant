import threading


def speak(text: str) -> None:
    clean = " ".join(text.split())
    if not clean:
        return

    threading.Thread(target=_speak_worker, args=(clean,), daemon=True).start()


def _speak_worker(text: str) -> None:
    try:
        import pyttsx3

        engine = pyttsx3.init()
        engine.setProperty("rate", 175)
        engine.say(text[:800])
        engine.runAndWait()
    except Exception:
        return
