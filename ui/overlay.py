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

        self.root = tk.Tk()
        self._setup_window()
        self._build_ui()

    # ── Window setup ──────────────────────────────────────────────────────────

    def _setup_window(self):
        root = self.root
        root.title("CursorPal")
        root.attributes("-topmost", True)
        root.configure(bg=DARK["bg"])
        root.geometry(f"{cfg.WINDOW_WIDTH}x{cfg.WINDOW_HEIGHT}")
        root.resizable(False, False)
        # Dark appearance on macOS
        try:
            root.tk.call("tk::unsupported::MacWindowStyle", "style", root._w, "document", "closeBox")
        except Exception:
            pass
        root.withdraw()

    # ── UI layout ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = self.root

        main = tk.Frame(root, bg=DARK["bg"])
        main.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        # ── Chat area ─────────────────────────────────────────────────────────
        self.streaming_text = StreamingText(main)
        self.streaming_text.pack(fill=tk.BOTH, expand=True, padx=0, pady=(4, 0))

        # ── Action badge ──────────────────────────────────────────────────────
        self.action_badge = ActionBadge(main)
        self.action_badge.pack(fill=tk.X)

        # ── Separator ─────────────────────────────────────────────────────────
        tk.Frame(main, bg=DARK["border"], height=1).pack(fill=tk.X)

        # ── Input area ────────────────────────────────────────────────────────
        self.input_area = InputArea(main, on_submit=self._on_submit, on_stop=self._on_stop)
        self.input_area.pack(fill=tk.X, side=tk.BOTTOM)

        # Dismiss on Escape
        root.bind("<Escape>", lambda e: self.hide())
        root.protocol("WM_DELETE_WINDOW", self.hide)

    # ── Show / hide ───────────────────────────────────────────────────────────

    def show_near_cursor(self):
        ns_pt = NSEvent.mouseLocation()
        sh_ns = NSScreen.mainScreen().frame().size.height
        cx = int(ns_pt.x)
        cy = int(sh_ns - ns_pt.y)

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w, h = cfg.WINDOW_WIDTH, cfg.WINDOW_HEIGHT
        m = cfg.WINDOW_EDGE_MARGIN

        x = cx + cfg.CURSOR_OFFSET_X
        y = cy + cfg.CURSOR_OFFSET_Y

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
        self.root.after(100, self.input_area.focus)

    def hide(self):
        if not self._visible:
            return
        self._visible = False
        self.root.withdraw()

    def toggle_visibility(self):
        if self._visible:
            self.hide()
        else:
            self.show()

    # ── Thread-safe UI updates ────────────────────────────────────────────────

    def append_narration(self, text: str, tag: str = "narration") -> None:
        self.root.after(0, self.streaming_text.append, text, tag)

    def show_action_badge(self, action_type: str | None, description: str | None) -> None:
        self.root.after(0, self.action_badge.show, action_type, description)

    def set_busy(self, busy: bool) -> None:
        self.root.after(0, self.input_area.set_enabled, not busy)

    def clear_chat(self) -> None:
        self.root.after(0, self.streaming_text.clear)
