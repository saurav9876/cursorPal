# CursorPal

An AI teacher that lives next to your cursor. Hold a hotkey, speak (or type) what you want to learn — CursorPal takes over your screen, does the task, and narrates every step so you learn along the way.

Powered by Claude's computer-use API.

---

## How it works

1. You speak or type a request ("show me how to open a new terminal tab")
2. CursorPal takes a screenshot and sends it to Claude
3. Claude plans the steps, clicks/types on your screen, and streams a live narration into the overlay
4. After each action a new screenshot is sent back to Claude so it can see the result and continue
5. When done, you've watched it happen and learned why each step was taken

---

## Requirements

- macOS (Apple Silicon or Intel)
- Python 3.13 via Homebrew
- An [Anthropic API key](https://console.anthropic.com/)
- Internet connection (for Claude API + speech transcription)

---

## Installation

### 1. Install Homebrew (if you don't have it)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2. Install Python 3.13 and tkinter

```bash
brew install python@3.13
brew install python-tk@3.13
```

### 3. Clone the repo

```bash
git clone https://github.com/saurav9876/cursorPal.git
cd cursorPal
```

### 4. Install Python dependencies

```bash
/opt/homebrew/bin/python3.13 -m pip install -r requirements.txt --break-system-packages
```

### 5. Set your Anthropic API key

Either export it in your shell:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

Or just launch the app — it will prompt you to enter and save it on first run.

### 6. Run

```bash
/opt/homebrew/bin/python3.13 main.py
```

---

## macOS Permissions

On first launch macOS will ask for two permissions. Grant both to Terminal (or your Python executable) in **System Settings → Privacy & Security**:

| Permission | Why |
|---|---|
| **Screen Recording** | So CursorPal can take screenshots and understand what's on screen |
| **Accessibility** | So the global hotkey (Cmd+Shift+Space) can be detected |
| **Microphone** | So you can use voice input (Option+Space) |

---

## Controls

| Hotkey | Action |
|---|---|
| `Cmd+Shift+Space` | Show / hide the CursorPal overlay |
| `Option+Space` (hold) | Hold to speak your request, release to send |
| `Esc` | Close the overlay |
| **Stop** button | Cancel a running task |

You can also type directly into the text box and press Enter.

---

## Project structure

```
cursorPal/
├── main.py              # Entry point — API key setup, permissions, launch
├── app.py               # Glue layer wiring all components together
├── config.py            # Settings and Claude system prompt
├── requirements.txt
├── agent/
│   ├── loop.py          # Claude computer-use streaming agent loop
│   ├── tools.py         # Maps Claude actions to macOS Quartz events
│   └── screenshot.py    # Retina-aware screen capture
├── voice/
│   ├── recorder.py      # Microphone recording via sounddevice
│   └── transcriber.py   # Speech-to-text via Google Speech Recognition
├── ui/
│   ├── overlay.py       # Floating always-on-top chat window
│   ├── mic_bubble.py    # Pulsing mic indicator shown while recording
│   ├── components.py    # StreamingText, ActionBadge, InputArea widgets
│   └── themes.py        # Dark color palette
├── input/
│   └── hotkey.py        # Global hotkey listener (pynput)
└── permissions/
    └── checker.py       # macOS permission detection and guidance
```
