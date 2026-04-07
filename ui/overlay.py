from __future__ import annotations
import tkinter as tk
from typing import Callable

from AppKit import NSEvent, NSScreen

from .themes import DARK
from .components import StreamingText, ActionBadge, InputArea
import config as cfg


class OverlayWindow:
    """Floating always-on-top overlay window for CursorPal."""

    def __init__(self, on_submit: Callable[[str], None], on_stop: Callable[[], None]):
        self._on_submit = on_submit
        self._on_stop = on_stop
        self._visible = False
        self._drag_x = 0
        self._drag_y = 0

        self.root = tk.Tk()
        self._setup_window()
        self._build_ui()

    # ── Window setup ──────────────────────────────────────────────────────────

    def _setup_window(self):
        root = self.root
        root.title("CursorPal")
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.attributes("-alpha", 0.0)   # start transparent for fade-in
        root.configure(bg=DARK["bg"])
        root.geometry(f"{cfg.WINDOW_WIDTH}x{cfg.WINDOW_HEIGHT}")
        root.withdraw()  # hidden initially

    # ── UI layout ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = self.root

        # Thin border frame
        outer = tk.Frame(root, bg=DARK["border"], padx=1, pady=1)
        outer.pack(fill=tk.BOTH, expand=True)

        inner = tk.Frame(outer, bg=DARK["bg"])
        inner.pack(fill=tk.BOTH, expand=True)

        # ── Header (draggable) ────────────────────────────────────────────────
        header = tk.Frame(inner, bg=DARK["header"], height=36)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        tk.Label(
            header,
            text="CursorPal",
            bg=DARK["header"],
            fg=DARK["text_secondary"],
            font=("SF Pro Text", 12, "bold"),
        ).pack(side=tk.LEFT, padx=12)

        close_btn = tk.Label(
            header,
            text="✕",
            bg=DARK["header"],
            fg=DARK["text_secondary"],
            font=("SF Pro Text", 13),
            cursor="hand2",
            padx=10,
        )
        close_btn.pack(side=tk.RIGHT)
        close_btn.bind("<Button-1>", lambda e: self.hide())

        # Drag bindings
        header.bind("<ButtonPress-1>", self._drag_start)
        header.bind("<B1-Motion>", self._drag_motion)
        for child in header.winfo_children():
            child.bind("<ButtonPress-1>", self._drag_start)
            child.bind("<B1-Motion>", self._drag_motion)

        # ── Chat area ─────────────────────────────────────────────────────────
        self.streaming_text = StreamingText(inner)
        self.streaming_text.pack(fill=tk.BOTH, expand=True)

        # ── Action badge ──────────────────────────────────────────────────────
        self.action_badge = ActionBadge(inner)
        self.action_badge.pack(fill=tk.X)

        # ── Separator ─────────────────────────────────────────────────────────
        tk.Frame(inner, bg=DARK["border"], height=1).pack(fill=tk.X)

        # ── Input area ────────────────────────────────────────────────────────
        self.input_area = InputArea(inner, on_submit=self._on_submit, on_stop=self._on_stop)
        self.input_area.pack(fill=tk.X)

        # Dismiss on Escape
        root.bind("<Escape>", lambda e: self.hide())

    # ── Drag ──────────────────────────────────────────────────────────────────

    def _drag_start(self, event):
        self._drag_x = event.x_root - self.root.winfo_x()
        self._drag_y = event.y_root - self.root.winfo_y()

    def _drag_motion(self, event):
        x = event.x_root - self._drag_x
        y = event.y_root - self._drag_y
        self.root.geometry(f"+{x}+{y}")

    # ── Show / hide ───────────────────────────────────────────────────────────

    def show_near_cursor(self):
        # AppKit uses bottom-left origin; convert to top-left for tkinter
        ns_pt = NSEvent.mouseLocation()
        sh_ns = NSScreen.mainScreen().frame().size.height
        cx = int(ns_pt.x)
        cy = int(sh_ns - ns_pt.y)  # flip Y axis

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w, h = cfg.WINDOW_WIDTH, cfg.WINDOW_HEIGHT
        m = cfg.WINDOW_EDGE_MARGIN

        x = cx + cfg.CURSOR_OFFSET_X
        y = cy + cfg.CURSOR_OFFSET_Y

        # Flip if too close to right/bottom edge
        if x + w + m > sw:
            x = cx - w - cfg.CURSOR_OFFSET_X
        if y + h + m > sh:
            y = cy - h - cfg.CURSOR_OFFSET_Y

        x = max(m, min(x, sw - w - m))
        y = max(m, min(y, sh - h - m))

        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def show(self):
        if self._visible:
            return
        self._visible = True
        self.show_near_cursor()
        self.root.deiconify()
        self.root.lift()
        self._fade(0.0, 0.97, steps=8, delay=18)
        # Focus input after fade (macOS needs a delay)
        self.root.after(150, self.input_area.focus)

    def hide(self):
        if not self._visible:
            return
        self._visible = False
        self._fade(0.97, 0.0, steps=8, delay=12, on_done=self.root.withdraw)

    def toggle_visibility(self):
        if self._visible:
            self.hide()
        else:
            self.show()

    def _fade(self, from_alpha: float, to_alpha: float, steps: int, delay: int, on_done=None):
        step_size = (to_alpha - from_alpha) / steps
        current = [from_alpha]

        def _step():
            current[0] += step_size
            clamped = max(0.0, min(1.0, current[0]))
            self.root.attributes("-alpha", clamped)
            if abs(current[0] - to_alpha) > 0.01:
                self.root.after(delay, _step)
            elif on_done:
                on_done()

        _step()

    # ── Thread-safe UI updates ────────────────────────────────────────────────

    def append_narration(self, text: str, tag: str = "narration") -> None:
        """Thread-safe: append text to chat area."""
        self.root.after(0, self.streaming_text.append, text, tag)

    def show_action_badge(self, action_type: str | None, description: str | None) -> None:
        """Thread-safe: update action badge."""
        self.root.after(0, self.action_badge.show, action_type, description)

    def set_busy(self, busy: bool) -> None:
        """Thread-safe: toggle input enabled state."""
        self.root.after(0, self.input_area.set_enabled, not busy)

    def clear_chat(self) -> None:
        """Thread-safe: clear chat area."""
        self.root.after(0, self.streaming_text.clear)
