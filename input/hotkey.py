from __future__ import annotations
import threading
from typing import Callable

try:
    from pynput import keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False

# All variants of the Option/Alt key pynput may report
_ALT_KEYS = (
    {keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r}
    if PYNPUT_AVAILABLE else set()
)
_CMD_KEYS = (
    {keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r}
    if PYNPUT_AVAILABLE else set()
)
_SHIFT_KEYS = (
    {keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r}
    if PYNPUT_AVAILABLE else set()
)


def _any(keys: set, pressed: set) -> bool:
    return bool(keys & pressed)


class HotkeyListener:
    """
    Listens globally for two hotkeys:
      - Cmd+Shift+Space  → toggle text overlay
      - Option+Space     → push-to-talk voice input

    All callbacks must be thread-safe (use root.after() inside them).
    """

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
        if (
            _any(_CMD_KEYS, self._pressed)
            and _any(_SHIFT_KEYS, self._pressed)
            and keyboard.Key.space in self._pressed
            and not self._toggle_fired
        ):
            self._toggle_fired = True
            self._on_toggle()

        # Option+Space → start voice (Cmd/Shift must NOT be held)
        if (
            _any(_ALT_KEYS, self._pressed)
            and keyboard.Key.space in self._pressed
            and not _any(_CMD_KEYS, self._pressed)
            and not _any(_SHIFT_KEYS, self._pressed)
            and not self._voice_active
        ):
            self._voice_active = True
            self._on_voice_press()

    def _on_release(self, key) -> None:
        self._pressed.discard(key)

        # Reset toggle guard
        if not (
            _any(_CMD_KEYS, self._pressed)
            and _any(_SHIFT_KEYS, self._pressed)
            and keyboard.Key.space in self._pressed
        ):
            self._toggle_fired = False

        # Option or Space released → stop voice
        if self._voice_active and (
            key in _ALT_KEYS or key == keyboard.Key.space
        ):
            self._voice_active = False
            self._on_voice_release()
