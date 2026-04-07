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
    Listens globally for two hotkeys:
      - Cmd+Shift+Space  → toggle text overlay
      - Option+Space     → push-to-talk (on_voice_press / on_voice_release)

    All callbacks must be thread-safe (use root.after() inside them).
    """

    # Cmd+Shift+Space
    TOGGLE_COMBO = {keyboard.Key.cmd, keyboard.Key.shift, keyboard.Key.space} if PYNPUT_AVAILABLE else set()
    # Option+Space
    VOICE_KEYS = {keyboard.Key.alt, keyboard.Key.space} if PYNPUT_AVAILABLE else set()

    def __init__(
        self,
        on_toggle: Callable[[], None],
        on_voice_press: Callable[[], None],
        on_voice_release: Callable[[], None],
    ):
        self._on_toggle = on_toggle
        self._on_voice_press = on_voice_press
        self._on_voice_release = on_voice_release
        self._pressed: set = set()
        self._toggle_fired = False
        self._voice_active = False
        self._listener = None

    def start(self) -> None:
        if not PYNPUT_AVAILABLE:
            print("[CursorPal] pynput not installed — hotkeys disabled.")
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

        # Cmd+Shift+Space → toggle overlay
        if self.TOGGLE_COMBO.issubset(self._pressed) and not self._toggle_fired:
            self._toggle_fired = True
            self._on_toggle()

        # Option+Space → start voice (only if Cmd not held, to avoid overlap)
        if (
            self.VOICE_KEYS.issubset(self._pressed)
            and keyboard.Key.cmd not in self._pressed
            and keyboard.Key.shift not in self._pressed
            and not self._voice_active
        ):
            self._voice_active = True
            self._on_voice_press()

    def _on_release(self, key) -> None:
        self._pressed.discard(key)

        # Reset toggle fire guard when combo breaks
        if not self.TOGGLE_COMBO.issubset(self._pressed):
            self._toggle_fired = False

        # Option or Space released → stop voice
        if self._voice_active and (
            key in (keyboard.Key.alt, keyboard.Key.space)
        ):
            self._voice_active = False
            self._on_voice_release()
