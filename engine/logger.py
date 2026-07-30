import json
import time


class JsonlLogger:
    def __init__(self, path):
        self.path = path

    def log(self, event, **data):
        record = {"ts": round(time.time(), 3), "event": event, **data}
        with open(self.path, "a") as f:
            f.write(json.dumps(record) + "\n")
