"""Global hotkey kill switch. Works regardless of which window has focus --
doesn't depend on the game client, this console, or any particular monitor."""
import threading
from pynput import keyboard

HOTKEY = keyboard.Key.f12
PAUSE_HOTKEY = keyboard.Key.f11  # toggles; tasks that support it hold between actions


class KillSwitch:
    def __init__(self, hotkey=HOTKEY, pause_hotkey=PAUSE_HOTKEY):
        self.hotkey = hotkey
        self.pause_hotkey = pause_hotkey
        self.triggered = threading.Event()
        self.paused = threading.Event()
        self._listener = keyboard.Listener(on_press=self._on_press)

    def _on_press(self, key):
        if key == self.hotkey:
            self.triggered.set()
        elif key == self.pause_hotkey:
            if self.paused.is_set():
                self.paused.clear()
            else:
                self.paused.set()

    def start(self):
        self._listener.start()

    def stop(self):
        self._listener.stop()
