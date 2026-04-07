from __future__ import annotations
import tkinter as tk
import math
from AppKit import NSEvent, NSScreen

from .themes import DARK

MIC_ICON = "🎙"
SIZE = 110  # window size


class MicBubble:
    """
    Small floating bubble near the cursor that shows mic recording state.
    Uses root as parent for Toplevel so it shares the same event loop.
    """

    def __init__(self, root: tk.Tk):
        self._root = root
        self._win: tk.Toplevel | None = None
        self._canvas: tk.Canvas | None = None
        self._label: tk.Label | None = None
        self._status: tk.Label | None = None
        self._anim_id: str | None = None
        self._anim_phase = 0.0

    # ── Public API ────────────────────────────────────────────────────────────

    def show_listening(self) -> None:
        self._root.after(0, self._show, "listening")

    def show_thinking(self) -> None:
        self._root.after(0, self._show, "thinking")

    def hide(self) -> None:
        self._root.after(0, self._hide)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _show(self, state: str) -> None:
        if self._win is None:
            self._build()
        self._position_near_cursor()
        self._win.deiconify()
        self._win.lift()
        self._win.attributes("-topmost", True)
        self._set_state(state)

    def _hide(self) -> None:
        if self._anim_id:
            self._root.after_cancel(self._anim_id)
            self._anim_id = None
        if self._win:
            self._win.withdraw()

    def _build(self) -> None:
        win = tk.Toplevel(self._root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.attributes("-alpha", 0.95)
        win.configure(bg=DARK["bg"])
        win.geometry(f"{SIZE}x{SIZE}")
        win.withdraw()

        canvas = tk.Canvas(
            win, width=SIZE, height=SIZE,
            bg=DARK["bg"], highlightthickness=0,
        )
        canvas.pack(fill=tk.BOTH, expand=True)

        # Outer pulse ring
        canvas.create_oval(10, 10, SIZE-10, SIZE-10, outline=DARK["accent"], width=2, tags="ring")

        # Mic icon label
        label = tk.Label(
            canvas, text=MIC_ICON,
            font=("SF Pro Text", 26),
            bg=DARK["bg"], fg=DARK["text_primary"],
        )
        canvas.create_window(SIZE//2, SIZE//2 - 6, window=label, tags="icon")

        # Status text
        status = tk.Label(
            canvas, text="Listening…",
            font=("SF Pro Text", 9),
            bg=DARK["bg"], fg=DARK["text_secondary"],
        )
        canvas.create_window(SIZE//2, SIZE - 16, window=status, tags="status")

        self._win = win
        self._canvas = canvas
        self._label = label
        self._status = status

    def _set_state(self, state: str) -> None:
        if self._anim_id:
            self._root.after_cancel(self._anim_id)
            self._anim_id = None

        if state == "listening":
            self._status.configure(text="Listening…", fg=DARK["text_action"])
            self._label.configure(fg="#ff5f5f")
            self._pulse()
        elif state == "thinking":
            self._status.configure(text="Transcribing…", fg=DARK["text_secondary"])
            self._label.configure(fg=DARK["accent"])
            self._spin()

    def _pulse(self) -> None:
        """Animate the ring pulsing in/out."""
        if not self._win or not self._canvas:
            return
        self._anim_phase = (self._anim_phase + 0.15) % (2 * math.pi)
        scale = 1.0 + 0.12 * math.sin(self._anim_phase)
        r = int((SIZE // 2 - 12) * scale)
        cx, cy = SIZE // 2, SIZE // 2
        self._canvas.coords("ring", cx - r, cy - r, cx + r, cy + r)
        self._canvas.itemconfig("ring", outline="#ff5f5f")
        self._anim_id = self._root.after(50, self._pulse)

    def _spin(self) -> None:
        """Animate the ring color cycling."""
        if not self._win or not self._canvas:
            return
        self._anim_phase = (self._anim_phase + 0.2) % (2 * math.pi)
        alpha = int(180 + 75 * math.sin(self._anim_phase))
        color = f"#{alpha:02x}6a{alpha:02x}"
        self._canvas.itemconfig("ring", outline=color)
        self._anim_id = self._root.after(60, self._spin)

    def _position_near_cursor(self) -> None:
        ns_pt = NSEvent.mouseLocation()
        sh = NSScreen.mainScreen().frame().size.height
        cx = int(ns_pt.x)
        cy = int(sh - ns_pt.y)

        sw = self._root.winfo_screenwidth()
        sh_tk = self._root.winfo_screenheight()

        x = cx - SIZE // 2
        y = cy - SIZE - 20  # above cursor

        # Keep on screen
        x = max(10, min(x, sw - SIZE - 10))
        y = max(10, min(y, sh_tk - SIZE - 10))

        self._win.geometry(f"{SIZE}x{SIZE}+{x}+{y}")
