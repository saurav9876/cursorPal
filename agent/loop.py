from __future__ import annotations
import threading
import json
from typing import Callable

from openai import OpenAI

from .screenshot import ScreenshotCapture
from .tools import ToolExecutor
import config as cfg

# Tool definition we hand to GPT-4o — same interface as before
COMPUTER_TOOL = {
    "type": "function",
    "function": {
        "name": "computer",
        "description": (
            "Control the macOS computer. Use this to take screenshots, click, type, "
            "press keys, scroll, and move the mouse."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "screenshot",
                        "left_click",
                        "right_click",
                        "double_click",
                        "mouse_move",
                        "left_click_drag",
                        "type",
                        "key",
                        "scroll",
                    ],
                    "description": "The action to perform.",
                },
                "coordinate": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "[x, y] screen coordinate for click/move/scroll actions.",
                },
                "start_coordinate": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "[x, y] start coordinate for drag.",
                },
                "end_coordinate": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "[x, y] end coordinate for drag.",
                },
                "text": {
                    "type": "string",
                    "description": "Text to type (for 'type' action).",
                },
                "key": {
                    "type": "string",
                    "description": "Key combo to press, e.g. 'cmd+t', 'Return', 'escape'.",
                },
                "direction": {
                    "type": "string",
                    "enum": ["up", "down", "left", "right"],
                    "description": "Scroll direction.",
                },
                "amount": {
                    "type": "number",
                    "description": "Scroll amount (lines).",
                },
            },
            "required": ["action"],
        },
    },
}


class AgentLoop:
    """Runs the OpenAI GPT-4o computer-use agentic loop in a background thread."""

    def __init__(
        self,
        api_key: str,
        screenshot_capture: ScreenshotCapture,
        tool_executor: ToolExecutor,
        on_text_chunk: Callable[[str, str], None],
        on_action: Callable[[str, str], None],
        on_done: Callable[[], None],
        on_error: Callable[[str], None],
        cancel_event: threading.Event,
    ):
        self._client = OpenAI(api_key=api_key)
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
        b64, w, h = self._sc.capture()

        messages = [
            {"role": "system", "content": cfg.SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "low"},
                    },
                    {"type": "text", "text": user_message},
                ],
            },
        ]

        while not self._cancel.is_set():
            # Drop old screenshots from history to stay within token limits
            self._trim_screenshots(messages)

            # Stream the response
            text, tool_calls = self._stream_turn(messages)

            if text:
                messages.append({"role": "assistant", "content": text})

            if not tool_calls:
                break

            # Build assistant message with tool calls
            messages.append({
                "role": "assistant",
                "content": text or "",
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {"name": "computer", "arguments": json.dumps(tc["input"])},
                    }
                    for tc in tool_calls
                ],
            })

            # Execute tools and collect results
            for tc in tool_calls:
                if self._cancel.is_set():
                    break
                result_content = self._executor.execute({"input": tc["input"]})

                # result_content is a list with an image dict
                if result_content and result_content[0].get("type") == "image":
                    img = result_content[0]["source"]
                    content = [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img['data']}",
                                "detail": "low",
                            },
                        }
                    ]
                else:
                    content = result_content[0].get("text", "done") if result_content else "done"

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": content if isinstance(content, str) else json.dumps(content),
                })

    def _trim_screenshots(self, messages: list) -> None:
        """Replace all but the last screenshot with a text placeholder to save tokens."""
        image_positions = []
        for i, msg in enumerate(messages):
            content = msg.get("content")
            if isinstance(content, list):
                for j, block in enumerate(content):
                    if isinstance(block, dict) and block.get("type") == "image_url":
                        image_positions.append((i, j))
            elif isinstance(content, str) and content.startswith("[screenshot]"):
                pass  # already trimmed

        # Keep only the last screenshot, replace the rest
        for i, j in image_positions[:-1]:
            messages[i]["content"][j] = {"type": "text", "text": "[screenshot]"}

    def _stream_turn(self, messages: list) -> tuple[str, list]:
        """Stream one API turn. Returns (full_text, tool_calls_list)."""
        full_text = ""
        tool_calls: dict[int, dict] = {}  # index → {id, input_buf}

        stream = self._client.chat.completions.create(
            model=cfg.OPENAI_MODEL,
            max_tokens=cfg.MAX_TOKENS,
            messages=messages,
            tools=[COMPUTER_TOOL],
            tool_choice="auto",
            stream=True,
        )

        for chunk in stream:
            if self._cancel.is_set():
                break

            delta = chunk.choices[0].delta if chunk.choices else None
            if delta is None:
                continue

            # Stream text
            if delta.content:
                full_text += delta.content
                self._on_text(delta.content, "narration")

            # Accumulate tool calls
            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index
                    if idx not in tool_calls:
                        tool_calls[idx] = {"id": tc_delta.id or "", "input_buf": ""}
                    if tc_delta.id:
                        tool_calls[idx]["id"] = tc_delta.id
                    if tc_delta.function and tc_delta.function.arguments:
                        tool_calls[idx]["input_buf"] += tc_delta.function.arguments

        # Parse tool call arguments
        result = []
        for idx in sorted(tool_calls):
            tc = tool_calls[idx]
            try:
                inp = json.loads(tc["input_buf"])
            except json.JSONDecodeError:
                inp = {}
            result.append({"id": tc["id"], "input": inp})

        return full_text, result
