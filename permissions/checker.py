import subprocess
import tkinter as tk
from PIL import ImageGrab

from ui.themes import DARK


class PermissionChecker:

    def check_screen_recording(self) -> bool:
        """Try a 1×1 grab. Black pixel = permission denied."""
        try:
            img = ImageGrab.grab(bbox=(0, 0, 1, 1))
            pixel = img.getpixel((0, 0))
            # All-zero RGBA = almost certainly a black placeholder from macOS
            if isinstance(pixel, (tuple, list)) and all(v == 0 for v in pixel):
                return False
            return True
        except Exception:
            return False

    def check_accessibility(self) -> bool:
        """Try osascript; an error message indicates no Accessibility permission."""
        result = subprocess.run(
            ["osascript", "-e", 'tell application "System Events" to get name of first process'],
            capture_output=True, text=True,
        )
        return result.returncode == 0

    def show_permission_dialog(self, root: tk.Tk, missing: list[str]) -> None:
        """Show a modal explaining what permissions are needed."""
        dialog = tk.Toplevel(root)
        dialog.title("CursorPal — Permissions Required")
        dialog.configure(bg=DARK["bg"])
        dialog.resizable(False, False)
        dialog.grab_set()

        tk.Label(
            dialog,
            text="CursorPal needs a couple of macOS permissions to work:",
            bg=DARK["bg"],
            fg=DARK["text_primary"],
            font=("SF Pro Text", 13),
            wraplength=360,
            pady=12,
        ).pack(padx=20)

        for perm in missing:
            tk.Label(
                dialog,
                text=f"  • {perm}",
                bg=DARK["bg"],
                fg=DARK["text_action"],
                font=("SF Mono", 12),
                anchor="w",
            ).pack(fill=tk.X, padx=24)

        tk.Label(
            dialog,
            text="\nGrant these to Terminal (or your Python executable) in:\nSystem Settings → Privacy & Security",
            bg=DARK["bg"],
            fg=DARK["text_secondary"],
            font=("SF Pro Text", 12),
            wraplength=360,
            justify=tk.LEFT,
        ).pack(padx=20, pady=8)

        btn_frame = tk.Frame(dialog, bg=DARK["bg"])
        btn_frame.pack(pady=(0, 16))

        def open_settings():
            subprocess.run([
                "open",
                "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture",
            ])

        tk.Button(
            btn_frame,
            text="Open System Settings",
            bg=DARK["accent"],
            fg="#ffffff",
            font=("SF Pro Text", 12),
            relief=tk.FLAT,
            padx=14,
            pady=6,
            cursor="hand2",
            command=open_settings,
        ).pack(side=tk.LEFT, padx=6)

        tk.Button(
            btn_frame,
            text="Continue Anyway",
            bg=DARK["bg_secondary"],
            fg=DARK["text_secondary"],
            font=("SF Pro Text", 12),
            relief=tk.FLAT,
            padx=14,
            pady=6,
            cursor="hand2",
            command=dialog.destroy,
        ).pack(side=tk.LEFT, padx=6)

        dialog.wait_window()
