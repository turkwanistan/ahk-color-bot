"""Global hotkey kill switch. Works regardless of which window has focus --
doesn't depend on the game client, this console, or any particular monitor."""
import threading
from pynput import keyboard

HOTKEY = keyboard.Key.f12


class KillSwitch:
    def __init__(self, hotkey=HOTKEY):
        self.hotkey = hotkey
        self.triggered = threading.Event()
        self._listener = keyboard.Listener(on_press=self._on_press)

    def _on_press(self, key):
        if key == self.hotkey:
            self.triggered.set()

    def start(self):
        self._listener.start()

    def stop(self):
        self._listener.stop()
