import sys

import time
import ctypes
from ctypes import wintypes
import subprocess
import threading
import re

# ============================================================================
# Windows Console 原生 API 核心定义
# ============================================================================
kernel32 = ctypes.windll.kernel32
user32 = ctypes.windll.user32

STD_INPUT_HANDLE = -10
STD_OUTPUT_HANDLE = -11

ENABLE_EXTENDED_FLAGS = 0x0080
ENABLE_QUICK_EDIT_MODE = 0x0040

class COORD(ctypes.Structure):
    _fields_ = [("X", wintypes.SHORT), ("Y", wintypes.SHORT)]

class SMALL_RECT(ctypes.Structure):
    _fields_ = [("Left", wintypes.SHORT), ("Top", wintypes.SHORT),
                ("Right", wintypes.SHORT), ("Bottom", wintypes.SHORT)]

class CONSOLE_SCREEN_BUFFER_INFO(ctypes.Structure):
    _fields_ = [("dwSize", COORD), ("dwCursorPosition", COORD),
                ("wAttributes", wintypes.WORD), ("srWindow", SMALL_RECT),
                ("dwMaximumWindowSize", COORD)]

class CHAR_UNION(ctypes.Union):
    _fields_ = [("UnicodeChar", wintypes.WCHAR), ("AsciiChar", wintypes.CHAR)]

class KEY_EVENT_RECORD(ctypes.Structure):
    _fields_ = [("bKeyDown", wintypes.BOOL), ("wRepeatCount", wintypes.WORD),
                ("wVirtualKeyCode", wintypes.WORD), ("wVirtualScanCode", wintypes.WORD),
                ("uChar", CHAR_UNION), ("dwControlKeyState", wintypes.DWORD)]

class EVENT_UNION(ctypes.Union):
    _fields_ = [("KeyEvent", KEY_EVENT_RECORD), ("Padding", wintypes.DWORD * 4)]

class INPUT_RECORD(ctypes.Structure):
    _fields_ = [("EventType", wintypes.WORD), ("Event", EVENT_UNION)]

kernel32.GetConsoleScreenBufferInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(CONSOLE_SCREEN_BUFFER_INFO)]
kernel32.ReadConsoleOutputCharacterW.argtypes = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, COORD, ctypes.POINTER(wintypes.DWORD)]
kernel32.WriteConsoleInputW.argtypes = [wintypes.HANDLE, ctypes.POINTER(INPUT_RECORD), wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
kernel32.SetConsoleTitleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetConsoleMode.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
kernel32.SetConsoleMode.argtypes = [wintypes.HANDLE, wintypes.DWORD]

# ============================================================================
# 防卡死与按键注入功能
# ============================================================================

def disable_quick_edit():
    """禁用鼠标点选冻结功能，防止误触导致程序假死"""
    hInput = kernel32.GetStdHandle(STD_INPUT_HANDLE)
    mode = wintypes.DWORD()
    if kernel32.GetConsoleMode(hInput, ctypes.byref(mode)):
        mode.value &= ~ENABLE_QUICK_EDIT_MODE
        mode.value |= ENABLE_EXTENDED_FLAGS
        kernel32.SetConsoleMode(hInput, mode.value)

def get_deep_active_text():
    """【深海拖网级读取】彻底无视滚动条偏移，暴力扫荡底部 300 行"""
    hConsole = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
    csbi = CONSOLE_SCREEN_BUFFER_INFO()
    if not kernel32.GetConsoleScreenBufferInfo(hConsole, ctypes.byref(csbi)):
        return ""
    
    width = csbi.dwSize.X
    win_bottom = csbi.srWindow.Bottom
    cursor_y = csbi.dwCursorPosition.Y
    
    # 找到理论上最深的数据行，再往下探100行作为安全冗余区
    max_search_y = min(csbi.dwSize.Y - 1, max(win_bottom, cursor_y) + 100)
    # 往上回溯 300 行（完全覆盖任何超长代码块）
    min_search_y = max(0, max_search_y - 300)
    
    lines = []
    for y in range(min_search_y, max_search_y + 1):
        buffer = ctypes.create_unicode_buffer(width)
        chars_read = wintypes.DWORD()
        if kernel32.ReadConsoleOutputCharacterW(hConsole, buffer, width, COORD(0, y), ctypes.byref(chars_read)):
            # 净化 NUL 字符防止截断
            line_text = buffer[:chars_read.value].replace('\x00', ' ')
            lines.append(line_text.rstrip())
            
    # 从底部往上踢掉没有任何文字的死空行
    while lines and not lines[-1].strip():
        lines.pop()
        
    # 保留最后 150 行的内容交给正则去分析
    return "\n".join(lines[-150:])

def send_keystroke_simulated(vk_code, char):
    """"""
    hInput = kernel32.GetStdHandle(STD_INPUT_HANDLE)
    scan_code = user32.MapVirtualKeyW(vk_code, 0)
    
    record_down = (INPUT_RECORD * 1)()
    record_down[0].EventType = 1 
    record_down[0].Event.KeyEvent.bKeyDown = True
    record_down[0].Event.KeyEvent.wRepeatCount = 1
    record_down[0].Event.KeyEvent.wVirtualKeyCode = vk_code
    record_down[0].Event.KeyEvent.wVirtualScanCode = scan_code
    record_down[0].Event.KeyEvent.uChar.UnicodeChar = char
    written = wintypes.DWORD()
    kernel32.WriteConsoleInputW(hInput, record_down, 1, ctypes.byref(written))
    
    # 50毫秒
    time.sleep(0.05)
    
    record_up = (INPUT_RECORD * 1)()
    record_up[0].EventType = 1 
    record_up[0].Event.KeyEvent.bKeyDown = False
    record_up[0].Event.KeyEvent.wRepeatCount = 1
    record_up[0].Event.KeyEvent.wVirtualKeyCode = vk_code
    record_up[0].Event.KeyEvent.wVirtualScanCode = scan_code
    record_up[0].Event.KeyEvent.uChar.UnicodeChar = char
    kernel32.WriteConsoleInputW(hInput, record_up, 1, ctypes.byref(written))

def send_enter(): send_keystroke_simulated(0x0D, '\r')
def send_y_and_enter(): send_keystroke_simulated(0x59, 'y'); time.sleep(0.1); send_enter()

def notify_trigger(msg):
    kernel32.SetConsoleTitleW(f"🚀 {msg} - Claude Code")
    time.sleep(1.0)
    kernel32.SetConsoleTitleW("Claude Code")

# ============================================================================
# 监控与自动化逻辑
# ============================================================================

def background_monitor(process):
    last_action_time = 0.0
    spinner = ["—", "\\", "|", "/"]
    tick_idx = 0
    
    while process.poll() is None:
        now = time.monotonic()
        
        # 呼吸灯指示器
        if now - last_action_time > 1.0:
            kernel32.SetConsoleTitleW(f"Claude Auto [{spinner[tick_idx]}]")
            tick_idx = (tick_idx + 1) % 4

        if now - last_action_time > 1.5:  
            raw_text = get_deep_active_text().lower()
            if not raw_text:
                time.sleep(0.3)
                continue
            
            # 清除所有多余空格、不可见排版字符
            flat_text = re.sub(r'\s+', ' ', raw_text.replace('\xa0', ' ').replace('\u200b', ' '))
            
            # 看到 1.yes，同时底下有 2.no 或 2.yes 或 esc，
            # 
            has_yes = bool(re.search(r'1\s*[\.\)]?\s*yes', flat_text))
            has_no_or_footer = bool(re.search(r'2\s*[\.\)]?\s*(no|yes)|esc\s*to\s*cancel|tab\s*to\s*amend|ctrl\s*\+\s*e', flat_text))
            
            if has_yes and has_no_or_footer:
                send_enter()
                notify_trigger("已自动确认(Enter)")
                last_action_time = time.monotonic()
                continue
            
            if bool(re.search(r'\(\s*y\s*/\s*n\s*\)|\[\s*y\s*/\s*n\s*\]', flat_text)):
                if "?" in flat_text[-300:] or ":" in flat_text[-300:]:
                    send_y_and_enter()
                    notify_trigger("已自动输入 Y")
                    last_action_time = time.monotonic()
                    continue
                
            if "press enter to continue" in flat_text or "press [enter]" in flat_text:
                send_enter()
                notify_trigger("已自动按回车")
                last_action_time = time.monotonic()
                continue

        time.sleep(0.3)

def main():
    kernel32.SetConsoleTitleW("Claude Code")
    disable_quick_edit()
    print("[*] 启动 Claude Code (防长文本截断 + 坦克级碾压版)")
    
    cmd_args = sys.argv[1:]
    cmd = "claude " + " ".join(f'"{a}"' if " " in a else a for a in cmd_args)
    if not cmd_args:
        cmd = "claude"
        
    try:
        process = subprocess.Popen(cmd, shell=True)
    except Exception as e:
        print(f"启动失败: {e}")
        return

    monitor_thread = threading.Thread(target=background_monitor, args=(process,), daemon=True)
    monitor_thread.start()

    try:
        process.wait()
    except KeyboardInterrupt:
        pass
    print("\n[*] Claude Code 已退出。")

if __name__ == "__main__":
    main()