"""Live-доска ч.2: сайт. Запуск: python live_board.py -> http://127.0.0.1:8081"""
import io
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import dota_core as C
import live_data as D

HOST = "127.0.0.1"
PORT = 8081
try:
    PORT = int(C.CFG.get("live_board_port", 8081))
except Exception:
    pass
def fmt_clock(s):
    try:
        s = int(float(s))
        return "%d:%02d" % (s // 60, s % 60)
    except Exception:
        return "?"


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="text/html; charset=utf-8"):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/board":
            self._send(200, json.dumps(D.get_board(), ensure_ascii=False),
                       "application/json; charset=utf-8")
            return
        if self.path not in ("/", "/board"):
            self._send(404, "nope")
            return
        b = D.get_board()
        tempo = b.get("tempo") or {}
        t1 = (tempo.get("60сек") or {}).get("золото_в_мин_факт", "-")
        t5 = (tempo.get("5мин") or {}).get("золото_в_мин_факт", "-")
        rows = []
        for i, p in enumerate(b.get("players") or [], 1):
            cls = "r" if p.get("team") == "radiant" else "d"
            rows.append("<tr><td>%d</td><td class='%s'>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s/%s</td></tr>" % (
                i, cls, p.get("team"), p.get("hero"), p.get("account_id") or "?",
                p.get("kda", "-"), p.get("gpm", "-"), p.get("xpm", "-")))
        if not rows:
            rows.append("<tr><td colspan=6>Игроков нет: матч не в OpenDota live. GSI дает только тебя + счет.</td></tr>")
        you = b.get("you") or {}
        sc = b.get("score") or {}
        h = []
        h.append("<!DOCTYPE html><html lang='ru'><head><meta charset='utf-8'>")
        h.append("<meta http-equiv='refresh' content='5'><title>Dota LIVE</title>")
        h.append("<style>body{background:#0d1117;color:#e6edf3;font-family:Consolas,monospace;margin:12px}")
        h.append("table{border-collapse:collapse;width:100%}th,td{border:1px solid #30363d;padding:5px 8px;font-size:14px}")
        h.append("th{background:#161b22}.r{color:#7ee787}.d{color:#ff7b72}")
        h.append(".badge{background:#161b22;border:1px solid #30363d;border-radius:6px;padding:2px 8px;margin-right:6px}")
        h.append(".meta{color:#8b949e;font-size:13px}.ev{color:#d2a8ff;font-size:13px}</style></head><body>")
        h.append("<h2>Match %s | %s | %s:%s | %s</h2>" % (
            b.get("match_id"), fmt_clock(b.get("clock")), sc.get("radiant"), sc.get("dire"), b.get("stage")))
        h.append("<div class='meta'>обновлено %s | GSI %sс | источник: %s | точек: %s | каждые 5с</div>" % (
            b.get("now"), b.get("gsi_age_sec"), b.get("players_src"), b.get("history_points")))
        h.append("<div style='margin-top:6px'><span class='badge'>tempo1m: %s</span>" % t1)
        h.append("<span class='badge'>tempo5m: %s</span>" % t5)
        h.append("<span class='badge'>you: %s %s gold=%s</span>" % (you.get("name"), you.get("kda"), you.get("gold")))
        h.append("<span class='badge'>spectator: %s</span></div>" % b.get("spectator"))
        h.append("<h3>Игроки (%d)</h3>" % len(b.get("players") or []))
        h.append("<table><tr><th>#</th><th>Команда</th><th>Герой</th><th>account</th><th>KDA</th><th>GPM/XPM</th></tr>")
        h.append("\n".join(rows) + "</table>")
        h.append("<h3>События</h3><div class='ev'>" + "<br>".join(b.get("events") or ["-"]) + "</div>")
        h.append("<div class='meta'><a style='color:#58a6ff' href='/api/board'>/api/board</a></div></body></html>")
        self._send(200, "\n".join(h))


def main():
    C.track_tick()
    srv = HTTPServer((HOST, PORT), H)
    print("Live-доска: http://%s:%d (обновление каждые 5с)" % (HOST, PORT))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

