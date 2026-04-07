from __future__ import annotations
import threading
import json
from typing import Callable

import anthropic

from .screenshot import ScreenshotCapture
from .tools import ToolExecutor
import config as cfg


class AgentLoop:
    """
    Runs the Claude computer-use agentic loop in a background thread.
    Streams narration to the UI and executes computer actions.
    """

    def __init__(
        self,
        api_key: str,
        screenshot_capture: ScreenshotCapture,
        tool_executor: ToolExecutor,
        on_text_chunk: Callable[[str, str], None],  # (text, tag)
        on_action: Callable[[str, str], None],       # (action_type, description)
        on_done: Callable[[], None],
        on_error: Callable[[str], None],
        cancel_event: threading.Event,
    ):
        self._client = anthropic.Anthropic(api_key=api_key)
        self._sc = screenshot_capture
        self._executor = tool_executor
        self._on_text = on_text_chunk
        self._on_action = on_action
        self._on_done = on_done
        self._on_error = on_error
        self._cancel = cancel_event

    def run(self, user_message: str) -> None:
        try:
            self._run(user_message)
        except Exception as exc:
            self._on_error(str(exc))
        finally:
            self._on_done()

    def _run(self, user_message: str) -> None:
        # Initial screenshot
        b64, w, h = self._sc.capture()

        tool_def = self._executor.build_tool_definition(w, h)

        messages = [{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": b64,
                    },
                },
                {
                    "type": "text",
                    "text": user_message,
                },
            ],
        }]

        while not self._cancel.is_set():
            content_blocks, stop_reason = self._stream_turn(messages, tool_def)

            if stop_reason == "end_turn" or not self._has_tool_use(content_blocks):
                break

            # Build assistant turn from collected blocks
            messages.append({"role": "assistant", "content": content_blocks})

            # Execute tool uses, collect results
            tool_results = []
            for block in content_blocks:
                if self._cancel.is_set():
                    break
                if block.get("type") == "tool_use":
                    result_content = self._executor.execute(block)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block["id"],
                        "content": result_content,
                    })

            messages.append({"role": "user", "content": tool_results})

    def _stream_turn(self, messages: list, tool_def: dict) -> tuple[list, str]:
        """Stream one API turn. Returns (content_blocks, stop_reason)."""
        content_blocks = []
        stop_reason = "end_turn"

        current_block: dict | None = None
        current_json_buf = ""

        with self._client.beta.messages.stream(
            model=cfg.ANTHROPIC_MODEL,
            max_tokens=cfg.MAX_TOKENS,
            system=cfg.SYSTEM_PROMPT,
            tools=[tool_def],
            messages=messages,
            betas=[cfg.COMPUTER_USE_BETA],
        ) as stream:
            for event in stream:
                if self._cancel.is_set():
                    break

                etype = event.type

                if etype == "content_block_start":
                    cb = event.content_block
                    if cb.type == "text":
                        current_block = {"type": "text", "text": ""}
                        current_json_buf = ""
                    elif cb.type == "tool_use":
                        current_block = {
                            "type": "tool_use",
                            "id": cb.id,
                            "name": cb.name,
                            "input": {},
                        }
                        current_json_buf = ""

                elif etype == "content_block_delta":
                    delta = event.delta
                    if current_block is None:
                        continue
                    if delta.type == "text_delta":
                        current_block["text"] += delta.text
                        self._on_text(delta.text, "narration")
                    elif delta.type == "input_json_delta":
                        current_json_buf += delta.partial_json

                elif etype == "content_block_stop":
                    if current_block is not None:
                        if current_block["type"] == "tool_use" and current_json_buf:
                            try:
                                current_block["input"] = json.loads(current_json_buf)
                            except json.JSONDecodeError:
                                current_block["input"] = {}
                        content_blocks.append(current_block)
                        current_block = None
                        current_json_buf = ""

                elif etype == "message_delta":
                    if hasattr(event, "delta") and hasattr(event.delta, "stop_reason"):
                        stop_reason = event.delta.stop_reason or "end_turn"

        return content_blocks, stop_reason

    def _has_tool_use(self, blocks: list) -> bool:
        return any(b.get("type") == "tool_use" for b in blocks)
