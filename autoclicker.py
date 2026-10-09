"""遊戲連點器 (Game Auto Clicker)

功能：
  - 滑鼠連點：間隔、隨機抖動、按鍵（左/右/中）、單擊/雙擊、次數（0 = 無限）
  - 鍵盤連按：指定任一按鍵，或用逗號輪流按（例如 1,2,e）
  - 按住模式：持續按住某個鍵或滑鼠鍵（例如按住 W 自動前進）
  - 熱鍵可自訂（支援滑鼠側鍵），可選「按住熱鍵才連點」
  - 只在指定視窗（遊戲）在前景時運作，切出去自動暫停（Windows）
  - 遊戲相容模式：用掃描碼送出按鍵，部分遊戲才吃得到（Windows）
  - 設定檔：每個遊戲存一組設定
  - 固定座標點擊、啟動倒數、時間上限、提示音、即時統計（次數 / CPS）

需求：pip install pynput
"""
import ctypes
import json
import random
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from pynput import keyboard, mouse

IS_WINDOWS = sys.platform == "win32"

BUTTONS = {"左鍵": mouse.Button.left, "右鍵": mouse.Button.right, "中鍵": mouse.Button.middle}
MODES = ["滑鼠", "鍵盤", "按住按鍵", "按住滑鼠"]
KEY_MODES = ("鍵盤", "按住按鍵")
HOLD_MODES = ("按住按鍵", "按住滑鼠")
TRIGGERS = ["切換", "按住才連點"]
SETTINGS_FILE = Path.home() / ".gameclicker.json"
PROFILES_FILE = Path.home() / ".gameclicker_profiles.json"
DEFAULTS = {
    "interval": "100", "jitter": "0", "count": "0", "button": "左鍵",
    "double": False, "mode": "滑鼠", "key": "space", "delay": "3",
    "use_pos": False, "x": "0", "y": "0",
    "hold": "20", "trigger": "切換", "limit": "0", "window": "",
    "compat": True, "beep": True,
    "hk_start": "f6", "hk_quit": "f7", "hk_pos": "f8", "hk_win": "f9",
}
HOTKEYS = [("hk_start", "開始 / 停止"), ("hk_quit", "結束程式"),
           ("hk_pos", "記錄滑鼠座標"), ("hk_win", "記錄目前視窗")]
PROFILE_KEYS = [k for k in DEFAULTS if not k.startswith("hk_")]
SEED_PROFILES = {
    "放置遊戲（快速連點）": {"interval": "50", "jitter": "10", "hold": "10"},
    "按住才連點（左鍵）": {"interval": "60", "jitter": "10", "trigger": "按住才連點", "delay": "0"},
    "技能輪放 1→2→3": {"mode": "鍵盤", "key": "1,2,3", "interval": "800", "jitter": "80"},
    "按住 W 自動前進": {"mode": "按住按鍵", "key": "w"},
}

# ---------------------------------------------------------------- Windows 專用


if IS_WINDOWS:
    import winsound
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    user32.VkKeyScanW.restype = ctypes.c_short
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]

    class _KI(ctypes.Structure):
        _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]

    class _MI(ctypes.Structure):
        _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                    ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]

    class _INPUT(ctypes.Structure):
        class _U(ctypes.Union):
            _fields_ = [("ki", _KI), ("mi", _MI)]
        _anonymous_ = ("u",)
        _fields_ = [("type", wintypes.DWORD), ("u", _U)]

    KEYEVENTF_EXTENDEDKEY, KEYEVENTF_KEYUP, KEYEVENTF_SCANCODE = 0x1, 0x2, 0x8
    # 方向鍵、Home/End/PgUp/PgDn、Insert/Delete、右 Ctrl/Alt、數字鍵盤 /、NumLock
    EXTENDED_VKS = {0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x2D, 0x2E, 0xA3, 0xA5, 0x6F, 0x90}

    def key_vk(key):
        if isinstance(key, keyboard.Key):
            return getattr(key.value, "vk", 0) or 0
        r = user32.VkKeyScanW(ord(key))
        return r & 0xFF if r != -1 else 0

    def send_scan_key(key, down):
        """用掃描碼送出按鍵（DirectInput / 原始輸入的遊戲才收得到）。成功回傳 True。"""
        vk = key_vk(key)
        scan = user32.MapVirtualKeyW(vk, 0) if vk else 0
        if not scan:
            return False
        flags = KEYEVENTF_SCANCODE | (0 if down else KEYEVENTF_KEYUP)
        if vk in EXTENDED_VKS:
            flags |= KEYEVENTF_EXTENDEDKEY
        inp = _INPUT(type=1)
        inp.ki = _KI(0, scan, flags, 0, 0)
        return user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp)) == 1

    def foreground_title():
        buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(user32.GetForegroundWindow(), buf, 256)
        return buf.value

    def beep(on):
        try:
            winsound.Beep(1400 if on else 800, 80)
        except (RuntimeError, OSError):
            pass
else:
    def send_scan_key(key, down):
        return False

    def foreground_title():
        return None

    def beep(on):
        pass


# ---------------------------------------------------------------- 共用小工具


def parse_keys(text):
    """'space' -> [Key.space]，'1, 2,e' -> ['1', '2', 'e']。有任何無效的鍵就回傳 []。"""
    keys = []
    for name in text.replace("，", ",").split(","):
        name = name.strip()
        if not name:
            continue
        key = name if len(name) == 1 else keyboard.Key.__members__.get(name.lower())
        if key is None:
            return []
        keys.append(key)
    return keys


def key_name(key):
    """把鍵盤 / 滑鼠事件換成熱鍵用的名字：f6、space、x1（滑鼠側鍵）……"""
    if isinstance(key, (keyboard.Key, mouse.Button)):
        return key.name
    ch = getattr(key, "char", None)
    if ch and ch.isprintable():
        return ch.lower()
    vk = getattr(key, "vk", None)
    return f"vk{vk}" if vk is not None else ""


def show(name):
    return {"x1": "滑鼠側鍵1", "x2": "滑鼠側鍵2"}.get(name, name.upper())


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def save_json(path, data):
    try:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError:
        pass


# ---------------------------------------------------------------- 連點引擎


class AutoClicker:
    def __init__(self):
        self.mouse = mouse.Controller()
        self.kb = keyboard.Controller()
        self.running = False
        self.paused = False  # 目前視窗不是指定的遊戲視窗
        self.clicks = 0
        self.started_at = 0.0
        self.thread = None

    def start(self, cfg):
        if self.running:
            return
        self.running = True
        self.paused = False
        self.clicks = 0
        self.started_at = 0.0
        self.thread = threading.Thread(target=self._loop, args=(cfg,), daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False

    def _sleep(self, ms):
        end = time.perf_counter() + ms / 1000
        while self.running and time.perf_counter() < end:
            time.sleep(min(0.005, max(0, end - time.perf_counter())))

    def _blocked(self, cfg):
        title = foreground_title() if cfg["window"] else None
        return title is not None and cfg["window"] not in title.lower()

    def _key(self, cfg, key, down):
        if cfg["compat"] and send_scan_key(key, down):
            return
        (self.kb.press if down else self.kb.release)(key)

    def _click(self, cfg, step):
        hold = cfg["hold"]
        if cfg["mode"] == "鍵盤":
            key = cfg["keys"][step % len(cfg["keys"])]
            self._key(cfg, key, True)
            if hold:
                self._sleep(hold)
            self._key(cfg, key, False)
            return
        if cfg["pos"]:
            self.mouse.position = cfg["pos"]
        for i in range(2 if cfg["double"] else 1):
            self.mouse.press(cfg["button"])
            if hold:
                self._sleep(hold)
            self.mouse.release(cfg["button"])
            if i == 0 and cfg["double"]:
                self._sleep(max(hold, 10))

    def _press_hold(self, cfg, held):
        if cfg["mode"] == "按住按鍵":
            for key in cfg["keys"]:
                self._key(cfg, key, True)
                held.append(key)
        else:
            if cfg["pos"]:
                self.mouse.position = cfg["pos"]
            self.mouse.press(cfg["button"])
            held.append(cfg["button"])

    def _release(self, cfg, held):
        while held:
            item = held.pop()
            if isinstance(item, mouse.Button):
                self.mouse.release(item)
            else:
                self._key(cfg, item, False)

    def _loop(self, cfg):
        held = []  # 還按著的鍵 / 滑鼠鍵，結束時一定要放開
        try:
            self._sleep(cfg["delay"] * 1000)
            self.started_at = time.perf_counter()
            end = self.started_at + cfg["limit"] * 60 if cfg["limit"] else None
            hold_mode = cfg["mode"] in HOLD_MODES
            step = 0
            while self.running:
                if end and time.perf_counter() >= end:
                    break
                self.paused = self._blocked(cfg)
                if hold_mode:
                    if self.paused and held:
                        self._release(cfg, held)
                    elif not self.paused and not held:
                        self._press_hold(cfg, held)
                    self._sleep(50)
                    continue
                if self.paused:
                    self._sleep(100)
                    continue
                self._click(cfg, step)
                step += 1
                self.clicks += 1
                if cfg["count"] and self.clicks >= cfg["count"]:
                    break
                self._sleep(max(1, cfg["interval"] + random.uniform(-cfg["jitter"], cfg["jitter"])))
        finally:
            self._release(cfg, held)
            self.running = False
            self.paused = False


# ---------------------------------------------------------------- 介面


class Grid:
    """一欄一欄往下排的小幫手。"""

    def __init__(self, parent):
        self.parent, self.r = parent, 0

    def add(self, label, widget):
        if label:
            ttk.Label(self.parent, text=label).grid(row=self.r, column=0, sticky="w", pady=3)
            widget.grid(row=self.r, column=1, columnspan=2, sticky="e", pady=3)
        else:
            widget.grid(row=self.r, column=0, columnspan=3, sticky="w", pady=3)
        self.r += 1


class App:
    def __init__(self, root):
        self.root = root
        root.title("遊戲連點器")
        root.resizable(False, False)
        root.attributes("-topmost", True)
        self.clicker = AutoClicker()
        self.mouse_ctl = mouse.Controller()
        self.hold_mode = False
        self.delay_until = 0.0
        self._was_running = False
        self.capturing = None  # 正在等使用者按下新熱鍵時，記錄是哪一個
        self.down = set()      # 目前按著的熱鍵（用來忽略長按的連發）
        self.hk = {}
        self.hold_trigger = False
        self.ml = None         # 滑鼠側鍵監聽（只在需要時才開，避免拖慢滑鼠）

        saved = dict(DEFAULTS)
        saved.update(load_json(SETTINGS_FILE, {}))
        self.v = {k: (tk.BooleanVar if isinstance(d, bool) else tk.StringVar)(value=saved[k])
                  for k, d in DEFAULTS.items()}
        if PROFILES_FILE.exists():
            self.profiles = load_json(PROFILES_FILE, {})
        else:
            self.profiles = {n: {**{k: DEFAULTS[k] for k in PROFILE_KEYS}, **p} for n, p in SEED_PROFILES.items()}
            save_json(PROFILES_FILE, self.profiles)

        outer = ttk.Frame(root, padding=10)
        outer.grid()

        bar = ttk.Frame(outer)
        bar.grid(row=0, sticky="ew")
        ttk.Label(bar, text="設定檔").grid(row=0, column=0)
        self.prof = tk.StringVar()
        self.prof_box = ttk.Combobox(bar, textvariable=self.prof, values=sorted(self.profiles), width=20)
        self.prof_box.grid(row=0, column=1, padx=6)
        self.prof_box.bind("<<ComboboxSelected>>", lambda _e: self.load_profile())
        for i, (text, cmd) in enumerate([("儲存", self.save_profile), ("刪除", self.del_profile)]):
            ttk.Button(bar, text=text, width=5, command=cmd).grid(row=0, column=2 + i, padx=(0, 4))

        nb = ttk.Notebook(outer)
        nb.grid(row=1, pady=8)
        basic = ttk.Frame(nb, padding=10)
        adv = ttk.Frame(nb, padding=10)
        nb.add(basic, text="基本")
        nb.add(adv, text="進階")

        g = Grid(basic)
        g.add("模式", ttk.Combobox(basic, values=MODES, textvariable=self.v["mode"], width=10, state="readonly"))
        g.add("點擊間隔 (毫秒)", ttk.Spinbox(basic, from_=1, to=600000, textvariable=self.v["interval"], width=10))
        g.add("隨機抖動 ± (毫秒)", ttk.Spinbox(basic, from_=0, to=600000, textvariable=self.v["jitter"], width=10))
        g.add("次數 (0=無限)", ttk.Spinbox(basic, from_=0, to=10**9, textvariable=self.v["count"], width=10))
        g.add("啟動倒數 (秒)", ttk.Spinbox(basic, from_=0, to=60, textvariable=self.v["delay"], width=10))
        g.add("滑鼠按鍵", ttk.Combobox(basic, values=list(BUTTONS), textvariable=self.v["button"], width=10, state="readonly"))
        g.add("鍵盤按鍵", ttk.Entry(basic, textvariable=self.v["key"], width=13))
        g.add(None, ttk.Label(basic, text="連點時可用逗號輪流按，如 1,2,e；按住時會同時按住", foreground="gray"))
        g.add(None, ttk.Checkbutton(basic, text="雙擊", variable=self.v["double"]))
        g.add(None, ttk.Checkbutton(basic, text="固定座標 (按記錄座標熱鍵設定)", variable=self.v["use_pos"]))
        pos = ttk.Frame(basic)
        ttk.Label(pos, text="座標 X / Y").grid(row=0, column=0, padx=(0, 8))
        ttk.Entry(pos, textvariable=self.v["x"], width=6).grid(row=0, column=1)
        ttk.Entry(pos, textvariable=self.v["y"], width=6).grid(row=0, column=2, padx=(4, 0))
        g.add(None, pos)

        g = Grid(adv)
        g.add("按下持續 (毫秒)", ttk.Spinbox(adv, from_=0, to=5000, textvariable=self.v["hold"], width=10))
        g.add("熱鍵觸發方式", ttk.Combobox(adv, values=TRIGGERS, textvariable=self.v["trigger"], width=10, state="readonly"))
        g.add("時間上限 (分鐘, 0=不限)", ttk.Spinbox(adv, from_=0, to=1440, textvariable=self.v["limit"], width=10))
        g.add("只在此視窗運作", ttk.Entry(adv, textvariable=self.v["window"], width=22))
        g.add(None, ttk.Label(adv, text="標題含此文字才會動；留空 = 不限（僅 Windows）", foreground="gray"))
        g.add(None, ttk.Checkbutton(adv, text="遊戲相容模式（掃描碼，僅 Windows）", variable=self.v["compat"]))
        g.add(None, ttk.Checkbutton(adv, text="開始 / 停止時發出提示音（僅 Windows）", variable=self.v["beep"]))
        ttk.Label(adv, text="熱鍵：按「設定」後，按下想用的鍵或滑鼠側鍵", foreground="gray").grid(
            row=g.r, column=0, columnspan=3, sticky="w", pady=(10, 2))
        g.r += 1
        self.cap_btns = {}
        for key, label in HOTKEYS:
            ttk.Label(adv, text=label).grid(row=g.r, column=0, sticky="w", pady=2)
            ttk.Entry(adv, textvariable=self.v[key], width=11, state="readonly").grid(row=g.r, column=1, sticky="e")
            btn = ttk.Button(adv, text="設定", width=7, command=lambda k=key: self.capture(k))
            btn.grid(row=g.r, column=2, padx=(4, 0))
            self.cap_btns[key] = btn
            g.r += 1

        self.btn = ttk.Button(outer, text="開始", command=self.toggle)
        self.btn.grid(row=2, sticky="ew", pady=(0, 4))
        self.status = ttk.Label(outer, text="已停止", foreground="gray")
        self.status.grid(row=3)
        self.tip = ttk.Label(outer, foreground="gray")
        self.tip.grid(row=4)

        self.kl = keyboard.Listener(on_press=lambda k: self._input(key_name(k), True),
                                    on_release=lambda k: self._input(key_name(k), False))
        self.kl.start()
        for key in [k for k, _ in HOTKEYS] + ["trigger"]:
            self.v[key].trace_add("write", self._sync_hotkeys)
        self._sync_hotkeys()
        root.protocol("WM_DELETE_WINDOW", self.quit)
        self._tick()

    # ---- 熱鍵

    def _post(self, fn, *args):
        try:
            self.root.after(0, fn, *args)
        except (RuntimeError, tk.TclError):
            pass  # 視窗已經關了

    def _sync_hotkeys(self, *_):
        self.hk = {k: self.v[k].get().strip().lower() for k, _ in HOTKEYS}
        self.hold_trigger = self.v["trigger"].get() == "按住才連點"
        need_mouse = bool(self.capturing) or any(n in ("x1", "x2") for n in self.hk.values())
        if need_mouse and not self.ml:
            self.ml = mouse.Listener(on_click=self._on_click)
            self.ml.start()
        elif not need_mouse and self.ml:
            self.ml.stop()
            self.ml = None
        s, q, p, w = (show(self.hk[k]) for k, _ in HOTKEYS)
        head = f"按住 {s} 連點" if self.hold_trigger else f"{s} 開始/停止"
        self.tip.config(text=f"{head}　{q} 結束　{p} 記錄座標　{w} 記錄視窗")
        self._refresh()

    def _on_click(self, _x, _y, button, pressed):
        if button.name in ("x1", "x2"):  # 注意：回傳 False 會讓監聽停掉，所以這裡不回傳值
            self._input(button.name, pressed)

    def capture(self, key):
        for b in self.cap_btns.values():
            b.config(text="設定")
        self.capturing = key
        self.cap_btns[key].config(text="請按鍵…")
        self._sync_hotkeys()

    def _set_hotkey(self, key, name):
        self.capturing = None
        self.cap_btns[key].config(text="設定")
        self.v[key].set(name)

    def _input(self, name, down):
        """鍵盤 / 滑鼠側鍵事件（在監聽執行緒裡跑，要動畫面一律用 _post）。"""
        if not name:
            return
        if not down:
            self.down.discard(name)
        elif name in self.down:
            return  # 長按的連發
        else:
            self.down.add(name)
            if self.capturing:
                key, self.capturing = self.capturing, None
                self._post(self._set_hotkey, key, name)
                return
        hk = self.hk
        if name == hk.get("hk_start"):
            if self.hold_trigger:
                self._post(self.begin, True) if down else self._post(self.clicker.stop)
            elif down:
                self._post(self.toggle)
        elif down and name == hk.get("hk_quit"):
            self._post(self.quit)
        elif down and name == hk.get("hk_pos"):
            self._post(self.record_pos)
        elif down and name == hk.get("hk_win"):
            self._post(self.record_win)

    # ---- 設定檔

    def _say(self, text, color="gray"):
        self.status.config(text=text, foreground=color)

    def save_profile(self):
        name = self.prof.get().strip()
        if not name:
            return self._say("請先在「設定檔」欄輸入名稱", "red")
        self.profiles[name] = {k: self.v[k].get() for k in PROFILE_KEYS}
        save_json(PROFILES_FILE, self.profiles)
        self.prof_box["values"] = sorted(self.profiles)
        self._say(f"已儲存設定檔「{name}」")

    def load_profile(self):
        name = self.prof.get().strip()
        if name not in self.profiles:
            return self._say("找不到這個設定檔", "red")
        data = {k: DEFAULTS[k] for k in PROFILE_KEYS}
        data.update(self.profiles[name])
        for k, val in data.items():
            self.v[k].set(val)
        self._say(f"已載入設定檔「{name}」")

    def del_profile(self):
        name = self.prof.get().strip()
        if name in self.profiles and messagebox.askyesno("刪除設定檔", f"確定刪除「{name}」？", parent=self.root):
            del self.profiles[name]
            save_json(PROFILES_FILE, self.profiles)
            self.prof_box["values"] = sorted(self.profiles)
            self.prof.set("")
            self._say(f"已刪除「{name}」")

    # ---- 開始 / 停止

    @staticmethod
    def _int(var, default, lo=0):
        try:
            return max(lo, int(float(var.get())))
        except (ValueError, tk.TclError):
            return default

    def _config(self):
        mode = self.v["mode"].get()
        keys = parse_keys(self.v["key"].get())
        if mode in KEY_MODES and not keys:
            self._say("無效的鍵盤按鍵", "red")
            return None
        x, y = self._int(self.v["x"], 0), self._int(self.v["y"], 0)
        return {
            "mode": mode,
            "interval": self._int(self.v["interval"], 100, 1),
            "jitter": self._int(self.v["jitter"], 0),
            "count": self._int(self.v["count"], 0),
            "delay": self._int(self.v["delay"], 0),
            "hold": self._int(self.v["hold"], 20),
            "limit": self._int(self.v["limit"], 0),
            "window": self.v["window"].get().strip().lower(),
            "compat": self.v["compat"].get(),
            "button": BUTTONS[self.v["button"].get()],
            "double": self.v["double"].get(),
            "keys": keys,
            "pos": (x, y) if self.v["use_pos"].get() else None,
        }

    def record_pos(self):
        x, y = self.mouse_ctl.position
        self.v["x"].set(str(int(x)))
        self.v["y"].set(str(int(y)))
        self.v["use_pos"].set(True)

    def record_win(self):
        title = foreground_title()
        if title:
            self.v["window"].set(title)

    def begin(self, from_hold=False):
        if self.clicker.running:
            return
        cfg = self._config()
        if cfg is None:
            return
        if from_hold:
            cfg["delay"] = 0  # 已經在遊戲裡按著熱鍵，不用倒數
        else:
            self.save()
        self.hold_mode = cfg["mode"] in HOLD_MODES
        self.clicker.start(cfg)
        self.delay_until = time.perf_counter() + cfg["delay"]

    def toggle(self):
        if self.clicker.running:
            self.clicker.stop()
        else:
            self.begin()

    def _refresh(self):
        s = show(self.hk["hk_start"])
        if self.clicker.running:
            self.btn.config(text=f"停止 ({s})")
        else:
            self.btn.config(text=f"開始 ({s})")
            extra = "" if self.hold_mode else f"（共 {self.clicker.clicks} 次）"
            self._say(f"已停止{extra}")

    def _tick(self):
        c = self.clicker
        running = c.running
        if running != self._was_running:
            self._was_running = running
            self._refresh()
            if self.v["beep"].get():
                threading.Thread(target=beep, args=(running,), daemon=True).start()
        if running:
            if not (c.started_at and time.perf_counter() >= c.started_at):
                left = max(0, self.delay_until - time.perf_counter())
                self._say(f"{left:.1f} 秒後開始…", "orange")
            elif c.paused:
                self._say(f"暫停中：目前視窗不是「{self.v['window'].get().strip()[:16]}」", "orange")
            elif self.hold_mode:
                self._say("按住中…", "green")
            else:
                elapsed = max(time.perf_counter() - c.started_at, 0.001)
                self._say(f"連點中… {c.clicks} 次　{c.clicks / elapsed:.1f} CPS", "green")
        self.root.after(100, self._tick)

    def save(self):
        save_json(SETTINGS_FILE, {k: v.get() for k, v in self.v.items()})

    def quit(self):
        self.clicker.stop()
        if self.clicker.thread:
            self.clicker.thread.join(1)  # 等它把按住的鍵放開
        self.kl.stop()
        if self.ml:
            self.ml.stop()
        self.save()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
