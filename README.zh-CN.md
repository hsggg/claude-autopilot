# 🤖 Claude Code Autopilot

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-lightgrey)](https://github.com)

> **Windows 专用控制台自动化工具。**  
> 通过底层 Windows Console API 实时读取 Claude Code 终端输出缓冲区，自动检测交互式提示并模拟按键确认，让你在长时间运行任务时无需一直守在屏幕前。

---

## 目录

- [功能](#功能)
- [系统要求](#系统要求)
- [安装](#安装)
- [用法](#用法)
- [工作原理](#工作原理)
- [支持的交互模式](#支持的交互模式)
- [注意事项](#注意事项)
- [技术细节](#技术细节)
- [许可证](#许可证)

---

## 功能

| 功能 | 说明 |
|------|------|
| 🖱️ **防误触冻结** | 自动禁用 QuickEdit 模式，防止鼠标点选导致程序假死 |
| 🧠 **智能提示识别** | 支持 `(y/n)`、`Press Enter to continue`、`1. Yes / 2. No` 等多种交互形态 |
| 🚀 **深水拖网读取** | 暴力扫描控制台底部 300 行，无视滚动条偏移，彻底消除截断盲区 |
| ⌨️ **重磅按键注入** | 50ms 物理延迟确保高负载下系统不吞键 |
| 💡 **呼吸灯标题** | 控制台标题实时显示运行状态，一眼可知是否活着 |
| 🔧 **零依赖** | 只依赖 Python 标准库 + Windows 原生 API（`kernel32` / `user32`），无需 `pip install` |

---

## 系统要求

- **操作系统：** Windows 10 或 Windows 11（依赖 Win32 Console API）
- **Python：** 3.7+（仅标准库）
- **Claude Code：** 已安装并在 `PATH` 环境变量中可用

---

## 安装

### 方式一：直接下载

```bash
curl -O https://raw.githubusercontent.com/hsggg/claude-autopilot/main/claude_autopilot.py
```

### 方式二：克隆仓库

```bash
git clone https://github.com/hsggg/claude-autopilot.git
cd claude-autopilot
```

> 无需 `pip install`，脚本只依赖 Python 标准库和 Windows 原生 API。

---

## 用法

### 基本用法

```bash
python claude_autopilot.py
```

等价于直接运行 `claude`，同时启动后台监控。

### 带参数启动

```bash
python claude_autopilot.py /path/to/project
python claude_autopilot.py -p "some prompt"
```

所有参数会原样透传给 `claude` 命令。

### 退出

按 `Ctrl+C` 即可退出，Claude Code 进程会随之结束。

---

## 工作原理

```
┌──────────────────────────────────────────────┐
│              Claude Code                      │
│         (子进程, 控制台输出)                    │
│                                                │
│  ┌─ 1. Yes ───────────────────────────────┐   │
│  │ 2. No                                 │   │
│  │ Esc to cancel                         │   │
│  └───────────────────────────────────────┘   │
└──────────────┬───────────────────────────────┘
               │ ReadConsoleOutputCharacterW (300 行深拖网)
               ▼
┌──────────────────────────────────────────────┐
│         Claude Code Autopilot                 │
│                                                │
│  1. 文本规整（清除不可见字符）                   │
│  2. 正则匹配交互模式                            │
│  3. 检测到 → 注入按键                          │
│  4. 等待 → 继续监控                            │
└──────────────────────────────────────────────┘
```

### 核心流程

1. **禁用 QuickEdit** — 防止鼠标误触导致程序冻结
2. **启动 Claude Code** — 作为子进程运行
3. **后台监控线程** — 每 300ms 扫描一次控制台缓冲区
4. **文本规整** — 清除零宽字符、不可见字符，折叠多余空白
5. **正则匹配** — 识别交互式提示模式
6. **按键注入** — 通过 `WriteConsoleInputW` 写入按键事件
7. **循环** — 继续监控下一轮输出

---

## 支持的交互模式

| 模式 | 触发动效 | 响应 |
|------|---------|------|
| `1. Yes / 2. No` / `1) Yes` | 同时检测到 `1.yes` 和 `2.no/yes`，伴有 `Esc to cancel` 或 `Tab to amend` | **Enter** |
| `(y/n)` / `[y/n]` | 输出尾部带有 `?` 或 `:` | **Y + Enter** |
| `Press Enter to continue` | 精确匹配 | **Enter** |
| `Press [Enter]` | 精确匹配 | **Enter** |

---

## 注意事项

### 平台限制

**Windows 专属。** 脚本深度依赖以下 Win32 API，**无法在 Linux / macOS 运行**：

- `kernel32.GetConsoleScreenBufferInfo` — 读取缓冲区信息
- `kernel32.ReadConsoleOutputCharacterW` — 读取屏幕文本
- `kernel32.WriteConsoleInputW` — 写入按键输入
- `user32.MapVirtualKeyW` — 虚拟键码映射

### 使用场景

- ✅ 个人效率工具 — 长时间 Claude Code 任务（批量重构、大型代码审查）时减少值守
- ✅ 自动化测试 / CI 场景
- ⚠️ 请勿用于绕过 Claude Code 的正常使用限制或违反服务条款

### 局限性

- 基于正则匹配，非 NLP 理解，仅识别固定形态的交互提示
- 极少数情况下可能误判包含相似文本的代码输出（已通过正则加固降低误触率）
- 需要 `claude` 命令在 `PATH` 中

---

## 技术细节

### Win32 API 清单

| API | 用途 |
|-----|------|
| `GetStdHandle(STD_INPUT_HANDLE / STD_OUTPUT_HANDLE)` | 获取控制台句柄 |
| `GetConsoleScreenBufferInfo` | 获取缓冲区尺寸、光标位置、窗口范围 |
| `ReadConsoleOutputCharacterW` | 从指定坐标读取 Unicode 字符 |
| `WriteConsoleInputW` | 向输入队列注入按键事件 |
| `SetConsoleTitleW` | 修改控制台标题（状态指示） |
| `MapVirtualKeyW` | 虚拟键码 → 扫描码转换 |
| `SetConsoleMode` / `GetConsoleMode` | 禁用 QuickEdit 模式 |

### 输入记录结构

```c
INPUT_RECORD {
  EventType: WORD           // 1 = KEY_EVENT
  Event: UNION {
    KeyEvent: {
      bKeyDown: BOOL        // 按下 / 释放
      wRepeatCount: WORD    // 重复计数
      wVirtualKeyCode: WORD // 虚拟键码 (0x0D = Enter, 0x59 = Y)
      uChar: { UnicodeChar, AsciiChar }
      dwControlKeyState: DWORD
    }
  }
}
```

---

## 许可证

[MIT License](LICENSE) — 自由使用、修改、分发，作者不承担任何责任。

---

