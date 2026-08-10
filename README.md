# 🤖 Claude Code Autopilot

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-lightgrey)](https://github.com)

> **Windows-only console automation tool for Claude Code.**  
> Reads the terminal output buffer via the native Windows Console API, detects interactive prompts, and auto-confirms them — so you can walk away during long-running sessions.

---

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [How It Works](#how-it-works)
- [Supported Prompt Patterns](#supported-prompt-patterns)
- [Caveats](#caveats)
- [Technical Details](#technical-details)
- [License](#license)

---

## Features

| Feature | Description |
|---------|-------------|
| 🖱️ **QuickEdit Guard** | Automatically disables QuickEdit mode to prevent accidental mouse clicks from freezing the process |
| 🧠 **Smart Prompt Detection** | Recognizes `(y/n)`, `Press Enter to continue`, `1. Yes / 2. No`, and similar patterns |
| 🚀 **Deep-Read Sweep** | Scans the bottom 300 lines of the console buffer, immune to scroll offset truncation |
| ⌨️ **Heavyweight Keystroke Injection** | 50ms physical delay between key-down and key-up — ensures no keystrokes are swallowed under load |
| 💡 **Breathing Title Bar** | The console title updates in real-time so you can tell at a glance whether it's alive |
| 🔧 **Zero Dependencies** | Uses only Python stdlib + native Win32 APIs (`kernel32` / `user32`); no `pip install` needed |

---

## Requirements

- **OS:** Windows 10 or Windows 11 (Win32 Console API required)
- **Python:** 3.7+ (stdlib only)
- **Claude Code:** installed and available on `PATH`

---

## Installation

### Option 1: Download

```bash
curl -O https://raw.githubusercontent.com/hsggg/claude-autopilot/main/claude_autopilot.py
```

### Option 2: Clone

```bash
git clone https://github.com/hsggg/claude-autopilot.git
cd claude-autopilot
```

> No `pip install` required. The script relies solely on Python's standard library and Windows native APIs.

---

## Usage

### Basic

```bash
python claude_autopilot.py
```

This runs `claude` and starts the background monitor.

### With Arguments

```bash
python claude_autopilot.py /path/to/project
python claude_autopilot.py -p "some prompt"
```

All arguments are forwarded verbatim to the `claude` command.

### Exit

Press `Ctrl+C` to terminate both the autopilot and the Claude Code process.

---

## How It Works

```
┌──────────────────────────────────────────────┐
│              Claude Code                      │
│         (subprocess, console output)           │
│                                                │
│  ┌─ 1. Yes ───────────────────────────────┐   │
│  │ 2. No                                 │   │
│  │ Esc to cancel                         │   │
│  └───────────────────────────────────────┘   │
└──────────────┬───────────────────────────────┘
               │ ReadConsoleOutputCharacterW (300-line sweep)
               ▼
┌──────────────────────────────────────────────┐
│         Claude Code Autopilot                 │
│                                                │
│  1. Normalize text (strip control chars)       │
│  2. Regex-match prompt patterns                │
│  3. Match → inject keystroke                   │
│  4. Wait → continue monitoring                 │
└──────────────────────────────────────────────┘
```

### Core Flow

1. **Disable QuickEdit** — prevents accidental freeze from mouse clicks
2. **Launch Claude Code** — spawns as a subprocess
3. **Background monitor thread** — polls the console buffer every 300ms
4. **Text normalization** — strips zero-width chars, collapses whitespace
5. **Regex matching** — detects interactive prompt patterns
6. **Keystroke injection** — simulates key input via `WriteConsoleInputW`
7. **Loop** — continues monitoring for the next prompt

---

## Supported Prompt Patterns

| Pattern | Trigger Condition | Response |
|---------|------------------|----------|
| `1. Yes / 2. No` / `1) Yes` | Both `1.yes` and `2.no/yes` present, with `Esc to cancel` or `Tab to amend` | **Enter** |
| `(y/n)` / `[y/n]` | Followed by `?` or `:` in the tail of the output | **Y + Enter** |
| `Press Enter to continue` | Exact match | **Enter** |
| `Press [Enter]` | Exact match | **Enter** |

---

## Caveats

### Platform Limitation

**Windows only.** This script relies on the following Win32 APIs and **will not run on Linux/macOS**:

- `kernel32.GetConsoleScreenBufferInfo` — buffer geometry
- `kernel32.ReadConsoleOutputCharacterW` — screen text capture
- `kernel32.WriteConsoleInputW` — keystroke injection
- `user32.MapVirtualKeyW` — virtual-key to scan-code mapping

### Appropriate Use

- ✅ Personal productivity tool — reduce hands-on time during long Claude Code tasks (bulk refactoring, large code reviews)
- ✅ Automation testing / CI pipelines
- ⚠️ Do not use to bypass Claude Code usage restrictions or violate terms of service

### Limitations

- Pattern-matching is regex-based, not NLP — it recognizes fixed prompt shapes, not arbitrary text
- May occasionally misinterpret code output that happens to match a prompt pattern (regex guards reduce this risk)
- Requires the `claude` command to be on `PATH`

---

## Technical Details

### Win32 API Reference

| API | Purpose |
|-----|---------|
| `GetStdHandle(STD_INPUT_HANDLE / STD_OUTPUT_HANDLE)` | Obtain console handles |
| `GetConsoleScreenBufferInfo` | Query buffer size, cursor position, window bounds |
| `ReadConsoleOutputCharacterW` | Read Unicode characters from the buffer at given coordinates |
| `WriteConsoleInputW` | Inject keystroke events into the input queue |
| `SetConsoleTitleW` | Update the console window title (status indicator) |
| `MapVirtualKeyW` | Convert virtual-key code to scan code |
| `SetConsoleMode` / `GetConsoleMode` | Toggle QuickEdit mode |

### Input Record Structure

```c
INPUT_RECORD {
  EventType: WORD           // 1 = KEY_EVENT
  Event: UNION {
    KeyEvent: {
      bKeyDown: BOOL        // pressed / released
      wRepeatCount: WORD
      wVirtualKeyCode: WORD // 0x0D = Enter, 0x59 = Y
      uChar: { UnicodeChar, AsciiChar }
      dwControlKeyState: DWORD
    }
  }
}
```

---

## License

[MIT License](LICENSE) — Free to use, modify, and distribute. No warranty expressed or implied.

---

## Contributing

PRs and Issues are welcome! If you encounter a new prompt pattern or have ideas for improvement, please [open an Issue](https://github.com/hsggg/claude-autopilot/issues).