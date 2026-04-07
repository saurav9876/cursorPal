from __future__ import annotations
import subprocess
import time
from typing import Callable

import Quartz

from .screenshot import ScreenshotCapture
import config as cfg

# ── Key name → macOS key code mapping (for osascript) ────────────────────────
# osascript keystroke uses the character; key code uses numeric codes.
KEY_CODE_MAP: dict[str, int] = {
    "return": 36, "enter": 36,
    "tab": 48,
    "space": 49,
    "delete": 51, "backspace": 51,
    "escape": 53, "esc": 53,
    "left": 123, "right": 124, "down": 125, "up": 126,
    "f1": 122, "f2": 120, "f3": 99, "f4": 118,
    "f5": 96, "f6": 97, "f7": 98, "f8": 100,
    "f9": 101, "f10": 109, "f11": 103, "f12": 111,
    "home": 115, "end": 119, "pageup": 116, "page_up": 116,
    "pagedown": 121, "page_down": 121,
    "forwarddelete": 117,
}

MODIFIER_MAP: dict[str, str] = {
    "ctrl": "control down",
    "control": "control down",
    "cmd": "command down",
    "command": "command down",
    "super": "command down",
    "alt": "option down",
    "option": "option down",
    "shift": "shift down",
}

# Quartz button constants
_LEFT = Quartz.kCGMouseButtonLeft
_RIGHT = Quartz.kCGMouseButtonRight


class ToolExecutor:
    """Translates Claude's computer-use tool calls into macOS actions via Quartz."""

    def __init__(
        self,
        screenshot_capture: ScreenshotCapture,
        on_action_callback: Callable[[str, str], None] | None = None,
    ):
        self._sc = screenshot_capture
        self._on_action = on_action_callback or (lambda t, d: None)

    def build_tool_definition(self, width: int, height: int) -> dict:
        return {
            "type": "computer_20250124",
            "name": "computer",
            "display_width_px": width,
            "display_height_px": height,
        }

    def execute(self, tool_use_block: dict) -> list[dict]:
        """Execute a computer tool_use block. Returns content list for tool_result."""
        inp = tool_use_block.get("input", {})
        action = inp.get("action", "")

        self._on_action(action, self._describe(action, inp))
        time.sleep(cfg.ACTION_PAUSE_SECONDS)

        if action == "screenshot":
            return self._do_screenshot()
        elif action == "left_click":
            x, y = inp["coordinate"]
            self._click(x, y, _LEFT)
        elif action == "right_click":
            x, y = inp["coordinate"]
            self._click(x, y, _RIGHT)
        elif action == "double_click":
            x, y = inp["coordinate"]
            self._double_click(x, y)
        elif action == "mouse_move":
            x, y = inp["coordinate"]
            self._move(x, y)
        elif action == "left_click_drag":
            sx, sy = inp["start_coordinate"]
            ex, ey = inp["end_coordinate"]
            self._drag(sx, sy, ex, ey)
        elif action == "type":
            self._type(inp.get("text", ""))
        elif action == "key":
            self._key(inp.get("key", ""))
        elif action == "scroll":
            x, y = inp["coordinate"]
            direction = inp.get("direction", "down")
            amount = int(inp.get("amount", 3))
            self._scroll(x, y, direction, amount)
        else:
            return [{"type": "text", "text": f"Unknown action: {action}"}]

        time.sleep(cfg.SCREENSHOT_DELAY)
        return self._do_screenshot()

    # ── Mouse ─────────────────────────────────────────────────────────────────

    def _move(self, x: float, y: float) -> None:
        pt = Quartz.CGPoint(x, y)
        ev = Quartz.CGEventCreateMouseEvent(None, Quartz.kCGEventMouseMoved, pt, _LEFT)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)
        time.sleep(0.05)

    def _click(self, x: float, y: float, button: int) -> None:
        pt = Quartz.CGPoint(x, y)
        self._move(x, y)
        down = Quartz.kCGEventLeftMouseDown if button == _LEFT else Quartz.kCGEventRightMouseDown
        up   = Quartz.kCGEventLeftMouseUp   if button == _LEFT else Quartz.kCGEventRightMouseUp
        for etype in (down, up):
            ev = Quartz.CGEventCreateMouseEvent(None, etype, pt, button)
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)
            time.sleep(0.05)

    def _double_click(self, x: float, y: float) -> None:
        pt = Quartz.CGPoint(x, y)
        self._move(x, y)
        for click_num in (1, 2):
            for etype in (Quartz.kCGEventLeftMouseDown, Quartz.kCGEventLeftMouseUp):
                ev = Quartz.CGEventCreateMouseEvent(None, etype, pt, _LEFT)
                Quartz.CGEventSetIntegerValueField(ev, Quartz.kCGMouseEventClickState, click_num)
                Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)
                time.sleep(0.05)

    def _drag(self, sx: float, sy: float, ex: float, ey: float) -> None:
        src = Quartz.CGPoint(sx, sy)
        dst = Quartz.CGPoint(ex, ey)
        self._move(sx, sy)
        ev = Quartz.CGEventCreateMouseEvent(None, Quartz.kCGEventLeftMouseDown, src, _LEFT)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)
        time.sleep(0.1)
        ev = Quartz.CGEventCreateMouseEvent(None, Quartz.kCGEventLeftMouseDragged, dst, _LEFT)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)
        time.sleep(0.1)
        ev = Quartz.CGEventCreateMouseEvent(None, Quartz.kCGEventLeftMouseUp, dst, _LEFT)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)

    def _scroll(self, x: float, y: float, direction: str, amount: int) -> None:
        self._move(x, y)
        dy = amount if direction == "up" else -amount
        ev = Quartz.CGEventCreateScrollWheelEvent(None, Quartz.kCGScrollEventUnitLine, 1, dy)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)

    # ── Keyboard ──────────────────────────────────────────────────────────────

    def _type(self, text: str) -> None:
        """Type text via clipboard paste — handles unicode and special chars."""
        proc = subprocess.run(["pbcopy"], input=text.encode("utf-8"), capture_output=True)
        if proc.returncode == 0:
            self._osascript('tell application "System Events" to keystroke "v" using command down')
        else:
            # Fallback: type char by char via osascript
            safe = text.replace('"', '\\"').replace("\\", "\\\\")
            self._osascript(f'tell application "System Events" to keystroke "{safe}"')

    def _key(self, combo: str) -> None:
        """Execute a key combo like 'ctrl+c', 'cmd+shift+t', 'Return', 'F5'."""
        parts = [p.strip().lower() for p in combo.replace("+", " ").split()]
        modifiers = []
        key_part = None

        for p in parts:
            if p in MODIFIER_MAP:
                modifiers.append(MODIFIER_MAP[p])
            else:
                key_part = p

        if key_part is None:
            return

        using = f" using {{{', '.join(modifiers)}}}" if modifiers else ""

        key_code = KEY_CODE_MAP.get(key_part)
        if key_code is not None:
            self._osascript(
                f'tell application "System Events" to key code {key_code}{using}'
            )
        else:
            # Single character keystroke
            char = key_part if len(key_part) == 1 else key_part
            self._osascript(
                f'tell application "System Events" to keystroke "{char}"{using}'
            )

    def _osascript(self, script: str) -> None:
        subprocess.run(["osascript", "-e", script], capture_output=True)

    # ── Screenshot ────────────────────────────────────────────────────────────

    def _do_screenshot(self) -> list[dict]:
        b64, _, _ = self._sc.capture()
        return [{
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": b64,
            },
        }]

    def _describe(self, action: str, inp: dict) -> str:
        if action == "left_click":
            return f"Clicking at {inp.get('coordinate')}"
        if action == "right_click":
            return f"Right-clicking at {inp.get('coordinate')}"
        if action == "double_click":
            return f"Double-clicking at {inp.get('coordinate')}"
        if action == "type":
            t = inp.get("text", "")
            return f'Typing: "{t[:30]}{"..." if len(t) > 30 else ""}"'
        if action == "key":
            return f"Key: {inp.get('key')}"
        if action == "scroll":
            return f"Scrolling {inp.get('direction', 'down')}"
        if action == "mouse_move":
            return f"Moving to {inp.get('coordinate')}"
        if action == "screenshot":
            return "Taking screenshot"
        return action
