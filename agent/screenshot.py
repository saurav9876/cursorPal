from __future__ import annotations
import base64
import io
import os
import subprocess
import tempfile
import tkinter as tk

from PIL import Image


class ScreenshotCapture:
    """Retina-aware full-screen capture using macOS screencapture command."""

    def __init__(self, tk_ref: tk.Misc):
        self._tk = tk_ref

    def capture(self) -> tuple[str, int, int]:
        """Returns (base64_png, logical_width, logical_height)."""
        logical_w = self._tk.winfo_screenwidth()
        logical_h = self._tk.winfo_screenheight()

        # Use system screencapture — reliable, no permission issues beyond Screen Recording
        path = tempfile.mktemp(suffix=".png")
        try:
            subprocess.run(["screencapture", "-x", "-t", "png", path], check=True)
            img = Image.open(path)
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

        # On Retina, screencapture gives 2× pixels — downscale to logical coords
        if img.width != logical_w or img.height != logical_h:
            img = img.resize((logical_w, logical_h), Image.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.standard_b64encode(buf.getvalue()).decode()
        return b64, logical_w, logical_h
