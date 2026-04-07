#!/usr/bin/env python3
"""
CursorPal — An AI teacher that lives next to your cursor.
Usage: python main.py
Hotkey: Cmd+Shift+Space to show/hide
"""

import sys
import tkinter as tk


def check_deps():
    missing = []
    for pkg in ["anthropic", "PIL", "pynput"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"[CursorPal] Missing packages: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt")
        sys.exit(1)


def get_api_key() -> str:
    """Return API key from config, or prompt user via a tk modal."""
    import config as cfg
    if cfg.ANTHROPIC_API_KEY:
        return cfg.ANTHROPIC_API_KEY

    # Build a minimal tk root just for the prompt
    root = tk.Tk()
    root.title("CursorPal Setup")
    root.configure(bg="#1a1a1f")
    root.resizable(False, False)

    result = {"key": None, "save": False}

    from ui.themes import DARK

    tk.Label(
        root,
        text="CursorPal",
        bg=DARK["bg"],
        fg=DARK["accent"],
        font=("SF Pro Text", 18, "bold"),
    ).pack(pady=(24, 4))

    tk.Label(
        root,
        text="Enter your Anthropic API key to get started:",
        bg=DARK["bg"],
        fg=DARK["text_secondary"],
        font=("SF Pro Text", 12),
    ).pack(pady=(0, 12))

    entry = tk.Entry(
        root,
        show="•",
        bg=DARK["bg_input"],
        fg=DARK["text_primary"],
        font=("SF Mono", 12),
        insertbackground=DARK["accent"],
        relief=tk.FLAT,
        highlightthickness=1,
        highlightbackground=DARK["border"],
        highlightcolor=DARK["accent"],
        width=44,
    )
    entry.pack(padx=24, ipady=6)
    entry.focus_set()

    save_var = tk.BooleanVar(value=True)
    tk.Checkbutton(
        root,
        text="Save to ~/.cursorpal_config",
        variable=save_var,
        bg=DARK["bg"],
        fg=DARK["text_secondary"],
        selectcolor=DARK["bg_input"],
        activebackground=DARK["bg"],
        font=("SF Pro Text", 11),
    ).pack(pady=8)

    def submit():
        key = entry.get().strip()
        if not key:
            return
        result["key"] = key
        result["save"] = save_var.get()
        root.destroy()

    tk.Button(
        root,
        text="Start CursorPal",
        bg=DARK["accent"],
        fg="#ffffff",
        font=("SF Pro Text", 13, "bold"),
        relief=tk.FLAT,
        padx=20,
        pady=8,
        cursor="hand2",
        command=submit,
    ).pack(pady=(4, 24))

    root.bind("<Return>", lambda e: submit())
    root.mainloop()

    if not result["key"]:
        print("[CursorPal] No API key provided. Exiting.")
        sys.exit(0)

    if result["save"]:
        cfg.save_api_key(result["key"])

    cfg.ANTHROPIC_API_KEY = result["key"]
    return result["key"]


def check_permissions():
    """Check macOS permissions and show guidance if missing."""
    from permissions.checker import PermissionChecker

    checker = PermissionChecker()
    missing = []

    if not checker.check_screen_recording():
        missing.append("Screen Recording — so CursorPal can see your screen")
    if not checker.check_accessibility():
        missing.append("Accessibility — so CursorPal can detect the hotkey")

    if missing:
        # Temporary root for dialog
        root = tk.Tk()
        root.withdraw()
        checker.show_permission_dialog(root, missing)
        root.destroy()


def main():
    check_deps()
    get_api_key()
    check_permissions()

    from app import App
    App().run()


if __name__ == "__main__":
    main()
