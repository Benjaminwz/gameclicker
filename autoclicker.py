"""遊戲連點器 (Game Auto Clicker)

功能：
  - 可設定點擊間隔（毫秒）、隨機抖動、滑鼠按鍵（左/右/中）
  - 單擊 / 雙擊、指定點擊次數（0 = 無限）
  - 全域熱鍵：F6 開始/停止、F7 結束程式（遊戲中也有效）

需求：pip install pynput
"""
import random
import threading
import time
import tkinter as tk
from tkinter import ttk

from pynput import keyboard, mouse

BUTTONS = {"左鍵": mouse.Button.left, "右鍵": mouse.Button.right, "中鍵": mouse.Button.middle}


class AutoClicker:
    def __init__(self):
        self.controller = mouse.Controller()
        self.running = False
        self.thread = None
        self.on_finish = lambda: None

    def start(self, interval_ms, jitter_ms, button, double, count):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(
            target=self._loop, args=(interval_ms, jitter_ms, button, double, count), daemon=True
        )
        self.thread.start()

    def stop(self):
        self.running = False

    def _loop(self, interval_ms, jitter_ms, button, double, count):
        done = 0
        while self.running and (count == 0 or done < count):
            self.controller.click(button, 2 if double else 1)
            done += 1
            delay = max(1, interval_ms + random.uniform(-jitter_ms, jitter_ms))
            end = time.perf_counter() + delay / 1000
            while self.running and time.perf_counter() < end:
                time.sleep(min(0.005, max(0, end - time.perf_counter())))
        self.running = False
        self.on_finish()


class App:
    def __init__(self, root):
        self.root = root
        root.title("遊戲連點器")
        root.resizable(False, False)
        root.attributes("-topmost", True)
        self.clicker = AutoClicker()
        self.clicker.on_finish = lambda: root.after(0, self._refresh)

        frm = ttk.Frame(root, padding=12)
        frm.grid()

        self.interval = tk.StringVar(value="100")
        self.jitter = tk.StringVar(value="0")
        self.count = tk.StringVar(value="0")
        self.button = tk.StringVar(value="左鍵")
        self.double = tk.BooleanVar(value=False)

        rows = [
            ("點擊間隔 (毫秒)", ttk.Spinbox(frm, from_=1, to=600000, textvariable=self.interval, width=10)),
            ("隨機抖動 ± (毫秒)", ttk.Spinbox(frm, from_=0, to=600000, textvariable=self.jitter, width=10)),
            ("點擊次數 (0=無限)", ttk.Spinbox(frm, from_=0, to=10**9, textvariable=self.count, width=10)),
            ("滑鼠按鍵", ttk.Combobox(frm, values=list(BUTTONS), textvariable=self.button, width=8, state="readonly")),
        ]
        for i, (label, widget) in enumerate(rows):
            ttk.Label(frm, text=label).grid(row=i, column=0, sticky="w", pady=3)
            widget.grid(row=i, column=1, sticky="e", pady=3)
        ttk.Checkbutton(frm, text="雙擊", variable=self.double).grid(row=4, column=0, columnspan=2, sticky="w")

        self.btn = ttk.Button(frm, text="開始 (F6)", command=self.toggle)
        self.btn.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(8, 4))
        self.status = ttk.Label(frm, text="已停止", foreground="gray")
        self.status.grid(row=6, column=0, columnspan=2)
        ttk.Label(frm, text="F6 開始/停止　F7 結束程式", foreground="gray").grid(row=7, column=0, columnspan=2)

        self.hotkeys = keyboard.GlobalHotKeys({
            "<f6>": lambda: root.after(0, self.toggle),
            "<f7>": lambda: root.after(0, self.quit),
        })
        self.hotkeys.start()
        root.protocol("WM_DELETE_WINDOW", self.quit)

    def _num(self, var, default):
        try:
            return max(0, int(float(var.get())))
        except ValueError:
            return default

    def toggle(self):
        if self.clicker.running:
            self.clicker.stop()
        else:
            self.clicker.start(
                max(1, self._num(self.interval, 100)),
                self._num(self.jitter, 0),
                BUTTONS[self.button.get()],
                self.double.get(),
                self._num(self.count, 0),
            )
        self._refresh()

    def _refresh(self):
        if self.clicker.running:
            self.btn.config(text="停止 (F6)")
            self.status.config(text="連點中…", foreground="green")
        else:
            self.btn.config(text="開始 (F6)")
            self.status.config(text="已停止", foreground="gray")

    def quit(self):
        self.clicker.stop()
        self.hotkeys.stop()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
