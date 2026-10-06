"""Launcher GUI. Add a new task by giving its module a DISPLAY_NAME, a
PARAMS spec, and a run(params, log_path, kill_switch=None) function -- it
shows up here automatically, no GUI changes needed."""
import ctypes
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import scrolledtext, ttk

import pyautogui

from engine import window
from engine.killswitch import KillSwitch
from run import TASKS, arm_window_corner_failsafe, coerce, window_title

BG = "#0d0f0d"
BG_PANEL = "#121412"
FG = "#33ff66"
FG_DIM = "#1c9e3f"
FG_ERROR = "#ff4444"
FONT = ("Consolas", 10)
FONT_BOLD = ("Consolas", 10, "bold")


def _use_dark_titlebar(root):
    """Windows 10/11 only -- cosmetic, safe to no-op elsewhere."""
    if sys.platform != "win32":
        return
    try:
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        value = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), ctypes.sizeof(value)
        )
    except Exception:
        pass  # cosmetic only -- never worth failing the app over


def _format_mmss(seconds):
    seconds = max(0, int(seconds))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


class BotGUI:
    def __init__(self, root):
        self.root = root
        root.title("AHK Color Bot Launcher")
        root.configure(bg=BG)
        _use_dark_titlebar(root)

        self.task_var = tk.StringVar(value=list(TASKS.keys())[0])
        self.kill_switch = None
        self.worker_thread = None
        self.log_path = None
        self.param_widgets = {}
        self.run_start_ts = None
        self.run_duration_s = None
        self.running = False

        self._build_style()
        self._build_ui()
        self._on_task_change()
        self._poll_log()
        self._tick_timer()

    def _build_style(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")  # only ttk theme that allows full color overrides on Windows

        style.configure(".", background=BG, foreground=FG, font=FONT)
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=FG, font=FONT)
        style.configure("Status.TLabel", background=BG, foreground=FG, font=FONT_BOLD)

        style.configure(
            "TButton", background=BG_PANEL, foreground=FG, font=FONT_BOLD,
            borderwidth=1, focusthickness=0,
        )
        style.map(
            "TButton",
            background=[("active", FG_DIM), ("disabled", BG)],
            foreground=[("disabled", FG_DIM)],
        )

        style.configure(
            "TEntry", fieldbackground=BG_PANEL, foreground=FG,
            insertcolor=FG, borderwidth=1,
        )
        style.configure(
            "TCombobox", fieldbackground=BG_PANEL, background=BG_PANEL,
            foreground=FG, arrowcolor=FG, borderwidth=1,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", BG_PANEL)],
            foreground=[("readonly", FG)],
            selectbackground=[("readonly", BG_PANEL)],
            selectforeground=[("readonly", FG)],
        )
        # the dropdown popup list itself is a plain tk listbox under the hood
        self.root.option_add("*TCombobox*Listbox.background", BG_PANEL)
        self.root.option_add("*TCombobox*Listbox.foreground", FG)
        self.root.option_add("*TCombobox*Listbox.selectBackground", FG_DIM)
        self.root.option_add("*TCombobox*Listbox.font", FONT)

    def _build_ui(self):
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill="x")
        ttk.Label(top, text="TASK:").grid(row=0, column=0, sticky="w")
        dropdown = ttk.Combobox(
            top, textvariable=self.task_var,
            values=list(TASKS.keys()), state="readonly",
        )
        dropdown.grid(row=0, column=1, sticky="ew", padx=5)
        dropdown.bind("<<ComboboxSelected>>", lambda e: self._on_task_change())
        top.columnconfigure(1, weight=1)

        self.params_frame = ttk.Frame(self.root, padding=10)
        self.params_frame.pack(fill="x")

        btn_frame = ttk.Frame(self.root, padding=10)
        btn_frame.pack(fill="x")
        self.start_btn = ttk.Button(btn_frame, text="[ START ]", command=self._on_start)
        self.start_btn.pack(side="left", padx=5)
        self.stop_btn = ttk.Button(
            btn_frame, text="[ STOP ]", command=self._on_stop, state="disabled"
        )
        self.stop_btn.pack(side="left", padx=5)
        self.status_var = tk.StringVar(value="STATUS: IDLE")
        ttk.Label(btn_frame, textvariable=self.status_var, style="Status.TLabel").pack(
            side="left", padx=15
        )

        time_frame = ttk.Frame(self.root, padding=(10, 0))
        time_frame.pack(fill="x")
        self.time_var = tk.StringVar(value="")
        ttk.Label(time_frame, textvariable=self.time_var, style="Status.TLabel").pack(
            side="left"
        )

        self.log_box = scrolledtext.ScrolledText(
            self.root, width=100, height=24, state="disabled",
            bg="black", fg=FG, insertbackground=FG,
            font=FONT, borderwidth=0, highlightthickness=1,
            highlightbackground=FG_DIM, highlightcolor=FG,
        )
        self.log_box.pack(fill="both", expand=True, padx=10, pady=10)

    def _on_task_change(self):
        for w in self.params_frame.winfo_children():
            w.destroy()
        self.param_widgets = {}

        task_module = TASKS[self.task_var.get()]
        for i, spec in enumerate(task_module.PARAMS):
            ttk.Label(self.params_frame, text=spec["label"].upper() + ":").grid(
                row=i, column=0, sticky="w", pady=2
            )
            var = tk.StringVar(value=str(spec["default"]))
            ttk.Entry(self.params_frame, textvariable=var, width=15).grid(
                row=i, column=1, sticky="w", padx=5, pady=2
            )
            self.param_widgets[spec["name"]] = (var, spec)

    def _collect_params(self):
        params = {}
        for name, (var, spec) in self.param_widgets.items():
            params[name] = coerce(spec, var.get())
        return params

    def _on_start(self):
        task_key = self.task_var.get()
        task_module = TASKS[task_key]
        params = self._collect_params()

        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
        os.makedirs(log_dir, exist_ok=True)
        self.log_path = os.path.join(log_dir, f"{task_key}_{int(time.time())}.jsonl")

        try:
            arm_window_corner_failsafe(window_title(task_module))
        except window.WindowNotFoundError as e:
            self.status_var.set(f"ERROR: {e}")
            return

        self.kill_switch = KillSwitch()
        self.kill_switch.start()

        def worker():
            try:
                task_module.run(params, self.log_path, kill_switch=self.kill_switch)
            finally:
                self.kill_switch.stop()
                self.root.after(0, self._on_finished)

        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()

        self.run_start_ts = time.time()
        self.run_duration_s = params.get("duration_s")
        self.running = True

        self.status_var.set(f"STATUS: RUNNING [{task_key}]")
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")

    def _on_stop(self):
        if self.kill_switch is not None:
            self.kill_switch.triggered.set()
        self.status_var.set("STATUS: STOPPING...")

    def _on_finished(self):
        self.running = False
        self.status_var.set("STATUS: IDLE")
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")

    def _tick_timer(self):
        if self.running and self.run_start_ts is not None and self.run_duration_s:
            elapsed = time.time() - self.run_start_ts
            remaining = max(0, self.run_duration_s - elapsed)
            self.time_var.set(f"REMAINING: {_format_mmss(remaining)}")
        self.root.after(500, self._tick_timer)

    def _poll_log(self):
        if self.log_path and os.path.exists(self.log_path):
            try:
                with open(self.log_path) as f:
                    lines = f.readlines()[-300:]
                self.log_box.config(state="normal")
                self.log_box.delete("1.0", tk.END)
                self.log_box.insert(tk.END, "".join(lines))
                self.log_box.see(tk.END)
                self.log_box.config(state="disabled")
            except OSError:
                pass
        self.root.after(500, self._poll_log)

    def on_close(self):
        if self.kill_switch is not None:
            self.kill_switch.triggered.set()
            self.kill_switch.stop()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = BotGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
