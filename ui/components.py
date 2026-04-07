from __future__ import annotations
import tkinter as tk
from .themes import DARK, ACTION_ICONS


class StreamingText(tk.Frame):
    """Scrollable, read-only text area with colored tags for different message types."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=DARK["bg"], **kwargs)
        self._build()

    def _build(self):
        self.text = tk.Text(
            self,
            bg=DARK["bg"],
            fg=DARK["text_primary"],
            font=("SF Mono", 12),
            wrap=tk.WORD,
            state=tk.DISABLED,
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=0,
            padx=12,
            pady=8,
            cursor="arrow",
            selectbackground=DARK["accent"],
        )
        scrollbar = tk.Scrollbar(self, command=self.text.yview, width=6)
        scrollbar.configure(bg=DARK["bg"], troughcolor=DARK["bg_secondary"])
        self.text.configure(yscrollcommand=scrollbar.set)

        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Configure tags
        self.text.tag_configure("narration", foreground=DARK["text_narration"])
        self.text.tag_configure("action",    foreground=DARK["text_action"])
        self.text.tag_configure("user",      foreground=DARK["text_user"])
        self.text.tag_configure("error",     foreground=DARK["text_error"])
        self.text.tag_configure("system",    foreground=DARK["text_secondary"])

    def append(self, text: str, tag: str = "narration") -> None:
        self.text.configure(state=tk.NORMAL)
        self.text.insert(tk.END, text, tag)
        self.text.see(tk.END)
        self.text.configure(state=tk.DISABLED)

    def clear(self) -> None:
        self.text.configure(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)
        self.text.configure(state=tk.DISABLED)


class ActionBadge(tk.Frame):
    """Amber pill that shows the current action CursorPal is about to execute."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=DARK["bg"], **kwargs)
        self.label = tk.Label(
            self,
            bg=DARK["bg_secondary"],
            fg=DARK["text_action"],
            font=("SF Pro Text", 11),
            padx=10,
            pady=3,
        )
        self.label.pack(fill=tk.X, padx=12, pady=(0, 4))
        self.label.pack_forget()  # hidden by default

    def show(self, action_type: str | None, description: str | None) -> None:
        if not action_type:
            self.label.pack_forget()
            return
        icon = ACTION_ICONS.get(action_type, ACTION_ICONS["default"])
        self.label.configure(text=f"{icon}  {description or action_type}")
        self.label.pack(fill=tk.X, padx=12, pady=(0, 4))

    def hide(self) -> None:
        self.label.pack_forget()


class InputArea(tk.Frame):
    """Text input + send/stop button."""

    def __init__(self, parent, on_submit, on_stop, **kwargs):
        super().__init__(parent, bg=DARK["bg_secondary"], **kwargs)
        self._on_submit = on_submit
        self._on_stop = on_stop
        self._busy = False
        self._build()

    def _build(self):
        self.configure(pady=8, padx=8)

        self.entry = tk.Text(
            self,
            bg=DARK["bg_input"],
            fg=DARK["text_primary"],
            font=("SF Pro Text", 13),
            wrap=tk.WORD,
            height=3,
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=DARK["border"],
            highlightcolor=DARK["accent"],
            padx=8,
            pady=6,
            insertbackground=DARK["accent"],
        )
        self.entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.entry.bind("<Return>", self._handle_return)
        self.entry.bind("<Shift-Return>", lambda e: None)  # allow newline

        self.btn = tk.Button(
            self,
            text="Send",
            bg=DARK["accent"],
            fg="#ffffff",
            font=("SF Pro Text", 12, "bold"),
            relief=tk.FLAT,
            borderwidth=0,
            padx=12,
            pady=6,
            cursor="hand2",
            command=self._handle_click,
            activebackground=DARK["accent_hover"],
            activeforeground="#ffffff",
        )
        self.btn.pack(side=tk.RIGHT, padx=(6, 0))

    def _handle_return(self, event):
        if not self._busy:
            self._submit()
        return "break"

    def _handle_click(self):
        if self._busy:
            self._on_stop()
        else:
            self._submit()

    def _submit(self):
        text = self.entry.get("1.0", tk.END).strip()
        if text:
            self.entry.delete("1.0", tk.END)
            self._on_submit(text)

    def get_text(self) -> str:
        return self.entry.get("1.0", tk.END).strip()

    def set_enabled(self, enabled: bool) -> None:
        self._busy = not enabled
        state = tk.NORMAL if enabled else tk.DISABLED
        self.entry.configure(state=state)
        self.btn.configure(
            text="Send" if enabled else "Stop",
            bg=DARK["accent"] if enabled else "#ff7070",
        )

    def focus(self) -> None:
        self.entry.focus_set()
