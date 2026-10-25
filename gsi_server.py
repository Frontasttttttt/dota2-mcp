"""GSI-приёмник: Dota 2 шлёт сюда POST с состоянием игры. Stdlib-only."""

import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

BASE = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE, "gsi_latest.json")
PORT = 3000
HOST = "127.0.0.1"

try:
    with open(os.path.join(BASE, "config.json"), encoding="utf-8") as f:
        _cfg = json.load(f)
    PORT = int(_cfg.get("gsi_port", 3000))
    HOST = _cfg.get("gsi_host", "127.0.0.1")
except Exception:
    pass

_lock = threading.Lock()
_last_seen = {"ts": 0.0}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/status":
            with _lock:
                ts = _last_seen["ts"]
            age = time.time() - ts if ts else -1
            self._send(
                200,
                {
                    "ok": True,
                    "listening": True,
                    "port": PORT,
                    "last_packet_age_sec": age,
                    "has_data": ts > 0,
                },
            )
        elif self.path in ("/", "/latest"):
            try:
                with open(STATE_FILE, encoding="utf-8") as f:
                    data = json.load(f)
                self._send(200, data)
            except FileNotFoundError:
                self._send(
                    200,
                    {
                        "ok": False,
                        "reason": "пока нет данных: зайди в матч и убедись что gsi_server.py запущен",
                    },
                )
            except Exception as e:
                self._send(500, {"ok": False, "error": str(e)})
        else:
            self._send(404, {"ok": False})

    def do_POST(self):
        if len(self.path) > 200:
            self._send(404, {"ok": False})
            return
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8", "replace") or "{}")
        except Exception:
            payload = {"_raw_error": "bad json"}
        payload["_received_at"] = time.time()
        try:
            with _lock:
                with open(STATE_FILE, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False)
                _last_seen["ts"] = payload["_received_at"]
            self._send(200, {"ok": True})

            # Реактивное оповещение C# WPF оверлея по Named Pipe (<1 мс)
            try:
                import live_data as D
                import pipe_server

                srv = pipe_server.get_pipe_server()
                if srv.is_connected():
                    srv.broadcast(D.get_board())
            except Exception:
                pass
        except Exception as e:
            self._send(500, {"ok": False, "error": str(e)})


def main():
    srv = HTTPServer((HOST, PORT), Handler)
    print("Dota2 MCP GSI слушаю http://%s:%d" % (HOST, PORT))
    print("Статус: http://%s:%d/status" % (HOST, PORT))
    print("Оставь окно открытым во время игры. Ctrl+C — остановить.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
