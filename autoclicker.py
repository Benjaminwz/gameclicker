"""遊戲連點器 (Game Auto Clicker)

功能：
  - 滑鼠連點：間隔、隨機抖動、按鍵（左/右/中）、單擊/雙擊、次數（0 = 無限）
  - 鍵盤連按：指定任一按鍵（例如 space、e、1）
  - 固定座標點擊：F8 記錄目前滑鼠位置
  - 啟動倒數、即時統計（次數 / CPS）
  - 設定自動儲存
  - 全域熱鍵：F6 開始/停止、F7 結束程式、F8 記錄座標

需求：pip install pynput
"""
import json
import random
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from pynput import keyboard, mouse

BUTTONS = {"左鍵": mouse.Button.left, "右鍵": mouse.Button.right, "中鍵": mouse.Button.middle}
SETTINGS_FILE = Path.home() / ".gameclicker.json"
DEFAULTS = {
    "interval": "100", "jitter": "0", "count": "0", "button": "左鍵",
    "double": False, "mode": "滑鼠", "key": "space", "delay": "3",
    "use_pos": False, "x": "0", "y": "0",
}


def parse_key(name):
    """'space' -> Key.space, 'e' -> 'e'。無效則回傳 None。"""
    name = name.strip()
    if not name:
        return None
    if len(name) == 1:
        return name
    return getattr(keyboard.Key, name.lower(), None)


class AutoClicker:
    def __init__(self):
        self.mouse = mouse.Controller()
        self.kb = keyboard.Controller()
        self.running = False
        self.clicks = 0
        self.started_at = 0.0
        self.on_finish = lambda: None

    def start(self, cfg):
        if self.running:
            return
        self.running = True
        self.clicks = 0
        self.started_at = 0.0
        threading.Thread(target=self._loop, args=(cfg,), daemon=True).start()

    def stop(self):
        self.running = False

    def _sleep(self, ms):
        end = time.perf_counter() + ms / 1000
        while self.running and time.perf_counter() < end:
            time.sleep(min(0.005, max(0, end - time.perf_counter())))

    def _loop(self, cfg):
        self._sleep(cfg["delay"] * 1000)
        self.started_at = time.perf_counter()
        while self.running and (cfg["count"] == 0 or self.clicks < cfg["count"]):
            if cfg["mode"] == "鍵盤":
                self.kb.tap(cfg["key"])
            else:
                if cfg["pos"]:
                    self.mouse.position = cfg["pos"]
                self.mouse.click(cfg["button"], 2 if cfg["double"] else 1)
            self.clicks += 1
            self._sleep(max(1, cfg["interval"] + random.uniform(-cfg["jitter"], cfg["jitter"])))
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
        self.mouse_ctl = mouse.Controller()

        saved = dict(DEFAULTS)
        try:
            saved.update(json.loads(SETTINGS_FILE.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
        self.v = {k: (tk.BooleanVar if isinstance(d, bool) else tk.StringVar)(value=saved[k])
                  for k, d in DEFAULTS.items()}

        frm = ttk.Frame(root, padding=12)
        frm.grid()
        r = 0

        def row(label, widget):
            nonlocal r
            ttk.Label(frm, text=label).grid(row=r, column=0, sticky="w", pady=3)
            widget.grid(row=r, column=1, columnspan=2, sticky="e", pady=3)
            r += 1

        row("模式", ttk.Combobox(frm, values=["滑鼠", "鍵盤"], textvariable=self.v["mode"], width=8, state="readonly"))
        row("點擊間隔 (毫秒)", ttk.Spinbox(frm, from_=1, to=600000, textvariable=self.v["interval"], width=10))
        row("隨機抖動 ± (毫秒)", ttk.Spinbox(frm, from_=0, to=600000, textvariable=self.v["jitter"], width=10))
        row("次數 (0=無限)", ttk.Spinbox(frm, from_=0, to=10**9, textvariable=self.v["count"], width=10))
        row("啟動倒數 (秒)", ttk.Spinbox(frm, from_=0, to=60, textvariable=self.v["delay"], width=10))
        row("滑鼠按鍵", ttk.Combobox(frm, values=list(BUTTONS), textvariable=self.v["button"], width=8, state="readonly"))
        row("鍵盤按鍵", ttk.Entry(frm, textvariable=self.v["key"], width=10))
        ttk.Checkbutton(frm, text="雙擊", variable=self.v["double"]).grid(row=r, column=0, sticky="w")
        r += 1

        ttk.Checkbutton(frm, text="固定座標 (F8 記錄)", variable=self.v["use_pos"]).grid(row=r, column=0, sticky="w")
        pos = ttk.Frame(frm)
        ttk.Entry(pos, textvariable=self.v["x"], width=5).grid(row=0, column=0)
        ttk.Entry(pos, textvariable=self.v["y"], width=5).grid(row=0, column=1, padx=(4, 0))
        pos.grid(row=r, column=1, columnspan=2, sticky="e")
        r += 1

        self.btn = ttk.Button(frm, text="開始 (F6)", command=self.toggle)
        self.btn.grid(row=r, column=0, columnspan=3, sticky="ew", pady=(8, 4))
        r += 1
        self.status = ttk.Label(frm, text="已停止", foreground="gray")
        self.status.grid(row=r, column=0, columnspan=3)
        r += 1
        ttk.Label(frm, text="F6 開始/停止　F7 結束　F8 記錄座標", foreground="gray").grid(row=r, column=0, columnspan=3)

        self.hotkeys = keyboard.GlobalHotKeys({
            "<f6>": lambda: root.after(0, self.toggle),
            "<f7>": lambda: root.after(0, self.quit),
            "<f8>": lambda: root.after(0, self.record_pos),
        })
        self.hotkeys.start()
        root.protocol("WM_DELETE_WINDOW", self.quit)
        self._tick()

    @staticmethod
    def _int(var, default, lo=0):
        try:
            return max(lo, int(float(var.get())))
        except ValueError:
            return default

    def _config(self):
        key = parse_key(self.v["key"].get())
        if self.v["mode"].get() == "鍵盤" and key is None:
            self.status.config(text="無效的鍵盤按鍵", foreground="red")
            return None
        x, y = self._int(self.v["x"], 0), self._int(self.v["y"], 0)
        return {
            "mode": self.v["mode"].get(),
            "interval": self._int(self.v["interval"], 100, 1),
            "jitter": self._int(self.v["jitter"], 0),
            "count": self._int(self.v["count"], 0),
            "delay": self._int(self.v["delay"], 0),
            "button": BUTTONS[self.v["button"].get()],
            "double": self.v["double"].get(),
            "key": key,
            "pos": (x, y) if self.v["use_pos"].get() else None,
        }

    def record_pos(self):
        x, y = self.mouse_ctl.position
        self.v["x"].set(str(int(x)))
        self.v["y"].set(str(int(y)))
        self.v["use_pos"].set(True)

    def toggle(self):
        if self.clicker.running:
            self.clicker.stop()
        else:
            cfg = self._config()
            if cfg is None:
                return
            self.save()
            self.clicker.start(cfg)
            self.delay_until = time.perf_counter() + cfg["delay"]
        self._refresh()

    def _refresh(self):
        if self.clicker.running:
            self.btn.config(text="停止 (F6)")
        else:
            self.btn.config(text="開始 (F6)")
            self.status.config(text=f"已停止（共 {self.clicker.clicks} 次）", foreground="gray")

    def _tick(self):
        c = self.clicker
        if c.running:
            if c.started_at and time.perf_counter() >= c.started_at:
                elapsed = max(time.perf_counter() - c.started_at, 0.001)
                self.status.config(text=f"連點中… {c.clicks} 次　{c.clicks / elapsed:.1f} CPS", foreground="green")
            else:
                left = max(0, self.delay_until - time.perf_counter())
                self.status.config(text=f"{left:.1f} 秒後開始…", foreground="orange")
        self.root.after(100, self._tick)

    def save(self):
        try:
            SETTINGS_FILE.write_text(
                json.dumps({k: v.get() for k, v in self.v.items()}, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass

    def quit(self):
        self.clicker.stop()
        self.hotkeys.stop()
        self.save()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
