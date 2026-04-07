from __future__ import annotations
import os
import json
from pathlib import Path

# Model
ANTHROPIC_MODEL = "claude-sonnet-4-6"
COMPUTER_USE_BETA = "computer-use-2025-01-01"

# Window
WINDOW_WIDTH = 420
WINDOW_HEIGHT = 560
CURSOR_OFFSET_X = 24
CURSOR_OFFSET_Y = 24
WINDOW_EDGE_MARGIN = 20

# Agent
MAX_TOKENS = 4096
ACTION_PAUSE_SECONDS = 0.4
SCREENSHOT_DELAY = 0.3

# Hotkey: Cmd+Shift+Space
HOTKEY_COMBO = "cmd+shift+space"

# Config file for API key persistence
CONFIG_FILE = Path.home() / ".cursorpal_config"

SYSTEM_PROMPT = """You are CursorPal, a friendly and enthusiastic AI teacher living next to the user's cursor on macOS.

Your job is to demonstrate how to accomplish tasks on the computer, narrating each step clearly as if teaching a student watching over your shoulder.

NARRATION STYLE:
- Speak in first person, present tense: "I'm clicking the File menu now..."
- Before each action, briefly explain WHY: "To open a new tab, I'll press Cmd+T because that's the keyboard shortcut..."
- Keep narration concise but educational — one or two sentences per action
- After completing the task, add a short "What you learned:" summary

BEHAVIOR:
- Always take a screenshot first to understand the current screen state
- Plan your steps before acting
- If something doesn't work as expected, explain what happened and adapt
- Be encouraging and patient

You have access to a computer tool for taking screenshots and controlling the mouse/keyboard."""


def load_api_key() -> str | None:
    """Load API key from environment or config file."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text())
            return data.get("api_key")
        except Exception:
            pass
    return None


def save_api_key(key: str) -> None:
    """Save API key to config file."""
    CONFIG_FILE.write_text(json.dumps({"api_key": key}))
    CONFIG_FILE.chmod(0o600)


# Load at import time
ANTHROPIC_API_KEY = load_api_key()
