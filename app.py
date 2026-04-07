from __future__ import annotations
import threading

from ui.overlay import OverlayWindow
from agent.screenshot import ScreenshotCapture
from agent.tools import ToolExecutor
from agent.loop import AgentLoop
from input.hotkey import HotkeyListener
import config as cfg


class App:
    """Glue layer: wires overlay ↔ agent ↔ hotkey."""

    def __init__(self):
        self._cancel_event = threading.Event()
        self._agent_thread: threading.Thread | None = None

        # Build UI first (creates self.overlay.root = tk.Tk())
        self.overlay = OverlayWindow(
            on_submit=self._handle_submit,
            on_stop=self._handle_stop,
        )

        # Agent components (need tk root for screenshot Retina detection)
        self._sc = ScreenshotCapture(tk_ref=self.overlay.root)
        self._executor = ToolExecutor(
            screenshot_capture=self._sc,
            on_action_callback=self._on_action,
        )

        # Global hotkey
        self._hotkey = HotkeyListener(
            callback=lambda: self.overlay.root.after(0, self.overlay.toggle_visibility)
        )

    def run(self) -> None:
        self._hotkey.start()
        self.overlay.show()  # show on launch
        self.overlay.root.mainloop()

    # ── Callbacks ─────────────────────────────────────────────────────────────

    def _handle_submit(self, text: str) -> None:
        if self._agent_thread and self._agent_thread.is_alive():
            return  # already running

        self._cancel_event.clear()
        self.overlay.clear_chat()
        self.overlay.append_narration(f"You: {text}\n\n", "user")
        self.overlay.set_busy(True)
        self.overlay.show_action_badge("screenshot", "Starting…")

        loop = AgentLoop(
            api_key=cfg.ANTHROPIC_API_KEY,
            screenshot_capture=self._sc,
            tool_executor=self._executor,
            on_text_chunk=lambda t, tag: self.overlay.append_narration(t, tag),
            on_action=self._on_action,
            on_done=lambda: self.overlay.root.after(0, self._on_agent_done),
            on_error=lambda e: self.overlay.append_narration(f"\n\nError: {e}\n", "error"),
            cancel_event=self._cancel_event,
        )

        self._agent_thread = threading.Thread(target=loop.run, args=(text,), daemon=True)
        self._agent_thread.start()

    def _handle_stop(self) -> None:
        self._cancel_event.set()

    def _on_action(self, action_type: str, description: str) -> None:
        self.overlay.show_action_badge(action_type, description)

    def _on_agent_done(self) -> None:
        self.overlay.set_busy(False)
        self.overlay.show_action_badge(None, None)
        self.overlay.append_narration("\n\n─── Done ───\n", "system")
