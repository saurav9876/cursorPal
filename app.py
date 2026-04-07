from __future__ import annotations
import threading
import speech_recognition as sr

from ui.overlay import OverlayWindow
from ui.mic_bubble import MicBubble
from agent.screenshot import ScreenshotCapture
from agent.tools import ToolExecutor
from agent.loop import AgentLoop
from input.hotkey import HotkeyListener
from voice.recorder import AudioRecorder
from voice.transcriber import Transcriber
import config as cfg


class App:
    """Glue layer: wires overlay ↔ agent ↔ hotkey ↔ voice."""

    def __init__(self):
        self._cancel_event = threading.Event()
        self._agent_thread: threading.Thread | None = None

        # UI (creates tk.Tk root)
        self.overlay = OverlayWindow(
            on_submit=self._handle_submit,
            on_stop=self._handle_stop,
        )

        # Mic bubble (shares the same tk root via Toplevel)
        self._mic_bubble = MicBubble(self.overlay.root)

        # Agent components
        self._sc = ScreenshotCapture(tk_ref=self.overlay.root)
        self._executor = ToolExecutor(
            screenshot_capture=self._sc,
            on_action_callback=self._on_action,
        )

        # Voice
        self._recorder = AudioRecorder()
        self._transcriber = Transcriber()

        # Hotkey
        self._hotkey = HotkeyListener(
            on_toggle=lambda: self.overlay.root.after(0, self.overlay.toggle_visibility),
            on_voice_press=self._on_voice_press,
            on_voice_release=self._on_voice_release,
        )

    def run(self) -> None:
        self._hotkey.start()
        self.overlay.show()
        self.overlay.root.mainloop()

    # ── Voice ─────────────────────────────────────────────────────────────────

    def _on_voice_press(self) -> None:
        """Called from hotkey thread when Option+Space is pressed."""
        self._recorder.start()
        self._mic_bubble.show_listening()

    def _on_voice_release(self) -> None:
        """Called from hotkey thread when Option+Space is released."""
        self._mic_bubble.show_thinking()
        # Transcribe in background so we don't block the hotkey thread
        threading.Thread(target=self._transcribe_and_submit, daemon=True).start()

    def _transcribe_and_submit(self) -> None:
        audio, samplerate = self._recorder.stop()
        try:
            text = self._transcriber.transcribe(audio, samplerate)
            self.overlay.root.after(0, self._mic_bubble.hide)
            # Show overlay if hidden, then submit
            self.overlay.root.after(0, self._voice_submit, text)
        except sr.UnknownValueError:
            self.overlay.root.after(0, self._mic_bubble.hide)
            self.overlay.append_narration("\n(Couldn't understand — please try again)\n", "error")
        except Exception as exc:
            self.overlay.root.after(0, self._mic_bubble.hide)
            self.overlay.append_narration(f"\nVoice error: {exc}\n", "error")

    def _voice_submit(self, text: str) -> None:
        """Ensure overlay is visible, then submit the transcribed text."""
        if not self.overlay._visible:
            self.overlay.show()
        # Small delay to let show() animate before submitting
        self.overlay.root.after(200, self._handle_submit, text)

    # ── Agent ─────────────────────────────────────────────────────────────────

    def _handle_submit(self, text: str) -> None:
        if self._agent_thread and self._agent_thread.is_alive():
            return

        self._cancel_event.clear()
        self.overlay.clear_chat()
        self.overlay.append_narration(f"You: {text}\n\n", "user")
        self.overlay.set_busy(True)
        self.overlay.show_action_badge("screenshot", "Starting…")

        loop = AgentLoop(
            api_key=cfg.OPENAI_API_KEY,
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
