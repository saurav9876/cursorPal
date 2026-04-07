from __future__ import annotations
import threading
from typing import Callable

try:
    from pynput import keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False


class HotkeyListener:
    """
    Listens globally for Cmd+Shift+Space and fires a callback.
    Runs in a daemon thread — callback must be thread-safe (use root.after).
    """

    TARGET = {keyboard.Key.cmd, keyboard.Key.shift, keyboard.Key.space} if PYNPUT_AVAILABLE else set()

    def __init__(self, callback: Callable[[], None]):
        self._callback = callback
        self._pressed: set = set()
        self._fired = False  # prevent repeat-fire while combo held
        self._listener: "keyboard.Listener | None" = None

    def start(self) -> None:
        if not PYNPUT_AVAILABLE:
            print("[CursorPal] pynput not installed — global hotkey disabled.")
            return
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.daemon = True
        self._listener.start()

    def stop(self) -> None:
        if self._listener:
            self._listener.stop()

    def _on_press(self, key) -> None:
        self._pressed.add(key)
        if self.TARGET.issubset(self._pressed) and not self._fired:
            self._fired = True
            self._callback()

    def _on_release(self, key) -> None:
        self._pressed.discard(key)
        if not self.TARGET.issubset(self._pressed):
            self._fired = False
