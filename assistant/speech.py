import threading

_engine_lock = threading.Lock()
_current_engine = None


def speak(text: str) -> None:
    clean = " ".join(text.split())
    if not clean:
        return

    threading.Thread(target=_speak_worker, args=(clean,), daemon=True).start()


def stop_speaking() -> None:
    with _engine_lock:
        engine = _current_engine
    if engine is not None:
        try:
            engine.stop()
        except Exception:
            pass


def _speak_worker(text: str) -> None:
    global _current_engine
    try:
        import pyttsx3

        engine = pyttsx3.init()
        with _engine_lock:
            _current_engine = engine

        engine.setProperty("rate", 175)
        engine.say(text[:800])
        engine.runAndWait()
    except Exception:
        return
    finally:
        with _engine_lock:
            if _current_engine is engine:
                _current_engine = None
