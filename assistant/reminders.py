import itertools
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class Reminder:
    id: int
    message: str
    due_at: datetime
    timer: threading.Timer


_counter = itertools.count(1)
_reminders: dict[int, Reminder] = {}


def add_reminder(seconds: int, message: str, callback) -> Reminder:
    reminder_id = next(_counter)

    def fire() -> None:
        _reminders.pop(reminder_id, None)
        callback(f"Reminder: {message}")

    timer = threading.Timer(seconds, fire)
    reminder = Reminder(
        id=reminder_id,
        message=message,
        due_at=datetime.now() + timedelta(seconds=seconds),
        timer=timer,
    )
    _reminders[reminder_id] = reminder
    timer.start()
    return reminder


def list_reminders() -> str:
    if not _reminders:
        return "No active reminders."

    lines = ["Active reminders:"]
    for reminder in sorted(_reminders.values(), key=lambda item: item.due_at):
        lines.append(
            f"{reminder.id}. {reminder.due_at.strftime('%I:%M %p')} - {reminder.message}"
        )
    return "\n".join(lines)


def cancel_reminder(reminder_id: int) -> str:
    reminder = _reminders.pop(reminder_id, None)
    if not reminder:
        return f"I could not find reminder {reminder_id}."
    reminder.timer.cancel()
    return f"Cancelled reminder {reminder_id}: {reminder.message}"


def clear_reminders() -> str:
    count = len(_reminders)
    for reminder in list(_reminders.values()):
        reminder.timer.cancel()
    _reminders.clear()
    return f"Cleared {count} reminder(s)."
