import voice_coach
import threading
import auto_accept
"""Dota 2 auto-watcher: следит за процессом dota2.exe и состоянием GSI,
пишет события в watcher_events.log + watcher_state.json. Stdlib-only.
Запуск: python watcher.py  (можно свернуть/в фон)
Остановка: Ctrl+C
"""
import io
import json
import os
import subprocess
import sys
import time

try:
    if sys.stdout is not None and hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

BASE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(BASE, "watcher_events.log")
STATE = os.path.join(BASE, "watcher_state.json")
GSI_FILE = os.path.join(BASE, "gsi_latest.json")
POLL = 2


def log(msg):
    line = "%s %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg)
    if sys.stdout is not None:
        try:
            print(line, flush=True)
        except Exception:
            pass
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def save_state(obj):
    try:
        with open(STATE, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def play_voice(filename):
    """Plays Drow Ranger voice line in background (0 tokens cost)."""
    try:
        paths = [
            os.path.join(r"C:\AI\desktop-control", filename),
            os.path.join(r"C:\AI\desktop-control\voices_drow", filename)
        ]
        target = next((p for p in paths if os.path.exists(p)), None)
        if target:
            sys.path.insert(0, r"C:\AI\desktop-control")
            import audio
            audio.play_audio(target)
    except Exception:
        pass


def notify(title, msg):
    """Windows-тост без модулей. Тихо игнорирует ошибки."""
    try:
        t = title.replace('"', "'")[:120]
        m = msg.replace('"', "'")[:200]
        ps = (
            "$xml=@\"\n"
            "<toast><visual><binding template='ToastGeneric'>"
            "<text>%s</text><text>%s</text>"
            "</binding></visual></toast>\n"
            "\"@; "
            "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime] | Out-Null; "
            "$doc=[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom, ContentType=WindowsRuntime]::new(); "
            "$doc.LoadXml($xml); "
            "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Dota2 MCP').Show("
            "[Windows.UI.Notifications.ToastNotification, Windows.UI.Notifications, ContentType=WindowsRuntime]::new($doc))"
        ) % (t, m)
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                        "-Command", ps], capture_output=True, timeout=15, creationflags=0x08000000)
    except Exception:
        pass


def dota_running():
    try:
        import psutil
        for p in psutil.process_iter(['name']):
            name = p.info.get('name')
            if name and name.lower() == 'dota2.exe':
                return True
        return False
    except Exception:
        pass
    try:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq dota2.exe", "/FO", "CSV", "/NH"],
                             capture_output=True, timeout=5, creationflags=0x08000000)
        txt = (out.stdout or b"").decode("utf-8", "replace").lower()
        return "dota2.exe" in txt
    except Exception:
        return False


def gsi_info():
    try:
        with open(GSI_FILE, encoding="utf-8") as f:
            d = json.load(f)
        age = time.time() - float(d.get("_received_at", 0))
        mp = d.get("map") or {}
        hero = (d.get("hero") or {}).get("name", "?")
        pl = d.get("player") or {}
        # spectator: hero id 0, team spectator
        spect = (pl.get("team_name") == "spectator") or ((d.get("hero") or {}).get("id", 1) in (0, None))
        ev = d.get("events") or []
        bld = d.get("buildings") or {}
        return {"age": age,
                "stage": mp.get("game_state"),
                "hero": hero,
                "spectator": spect,
                "matchid": mp.get("matchid"),
                "score": "%s:%s" % (mp.get("radiant_score", "?"), mp.get("dire_score", "?")),
                "clock": mp.get("clock_time", mp.get("game_time")),
                "kda": "%s/%s/%s" % (pl.get("kills", "?"), pl.get("deaths", "?"), pl.get("assists", "?")),
                "gpm": pl.get("gold_per_min"),
                "hp": (d.get("hero") or {}).get("health"),
                "events_n": len(ev),
                "has_buildings": bool(bld),
                "paused": mp.get("paused")}
    except Exception:
        return None


def start_background_servers():
    """Запускает GSI-приёмник (порт 3000) и Live HUD (порт 8081) в фоновых потоках."""
    # 1. GSI сервер
    try:
        import gsi_server
        def _run_gsi():
            try:
                srv = gsi_server.HTTPServer((gsi_server.HOST, gsi_server.PORT), gsi_server.Handler)
                log("GSI сервер запущен на http://%s:%d" % (gsi_server.HOST, gsi_server.PORT))
                srv.serve_forever()
            except OSError as e:
                log("GSI сервер порт %d уже занят (возможно запущен отдельно): %s" % (gsi_server.PORT, e))
            except Exception as e:
                log("GSI сервер ошибка: %s" % e)
        t_gsi = threading.Thread(target=_run_gsi, daemon=True, name="GSIServerThread")
        t_gsi.start()
    except Exception as e:
        log("Не удалось запустить GSI сервер: %s" % e)

    # 2. Live HUD 2.0 (локальный сайт)
    try:
        import live_board
        def _run_board():
            try:
                live_board.C.track_tick()
                live_board.start_pipe_broadcaster()
                srv = live_board.HTTPServer((live_board.HOST, live_board.PORT), live_board.H)
                log("Live HUD 2.0 (локальный сайт) запущен на http://%s:%d" % (live_board.HOST, live_board.PORT))
                srv.serve_forever()
            except OSError as e:
                log("Live HUD порт %d уже занят (возможно запущен отдельно): %s" % (live_board.PORT, e))
            except Exception as e:
                log("Live HUD ошибка: %s" % e)
        t_board = threading.Thread(target=_run_board, daemon=True, name="LiveBoardThread")
        t_board.start()
    except Exception as e:
        log("Не удалось запустить Live HUD: %s" % e)



OVERLAY_EXE = os.path.join(BASE, "overlay_bin", "DotaOverlay.Wpf.exe")
_overlay_proc = None


def start_overlay():
    global _overlay_proc
    if _overlay_proc is not None and _overlay_proc.poll() is None:
        return
    if os.path.exists(OVERLAY_EXE):
        try:
            si = subprocess.STARTUPINFO()
            si.lpDesktop = r"winsta0\default"
            _overlay_proc = subprocess.Popen([OVERLAY_EXE], startupinfo=si, creationflags=0x08000000)
            log("WPF In-Game Overlay запущен (PID %d)" % _overlay_proc.pid)
        except Exception as e:
            log("Не удалось запустить WPF In-Game Overlay: %s" % e)


def stop_overlay():
    global _overlay_proc
    if _overlay_proc is not None:
        try:
            _overlay_proc.terminate()
            log("WPF In-Game Overlay остановлен")
        except Exception:
            pass
        _overlay_proc = None

def main():
    start_background_servers()
    log("watcher старт (опрос каждые %d c)" % POLL)
    was_running = None
    last_stage = None
    last_hero = None
    match_start = None
    while True:
        try:
            running = dota_running()
            if was_running is None:
                was_running = running
                log("dota2.exe: %s" % ("запущена" if running else "не найдена"))
                save_state({"dota_running": running, "ts": time.time()})
                if running:
                    start_overlay()
            elif running != was_running:
                was_running = running
                if running:
                    log("EVENT: Dota 2 ЗАПУЩЕНА")
                    notify("Dota 2 MCP", "Дота запущена. HUD: http://127.0.0.1:8081 | Оверлей: F8")
                    start_overlay()
                else:
                    log("EVENT: Dota 2 ЗАКРЫТА")
                    notify("Dota 2 MCP", "Дота закрыта.")
                    stop_overlay()
                    last_stage = None
                    match_start = None
                save_state({"dota_running": running, "ts": time.time()})

            if running:
                g = gsi_info()
                fresh = g is not None and g["age"] < 15
                stage = g["stage"] if g else None
                if g and fresh and stage != last_stage:
                    if g.get("spectator"):
                        log("EVENT: стадия -> %s [SPECTATE матч %s счёт %s время %s]" % (stage, g.get("matchid"), g.get("score"), g["clock"]))
                    else:
                        log("EVENT: стадия -> %s (герой %s, время %s)" % (stage, g["hero"], g["clock"]))
                    last_stage = stage
                    if stage == "DOTA_GAMERULES_STATE_HERO_SELECTION":
                        log("EVENT: СТАДИЯ ВЫБОРА ГЕРОЕВ (Радар лобби и смурф-детектор активны)")
                        notify("Выбор героев", "Радар лобби активен! Проверяю смурфов и сигнатурки игроков.")
                        voice_coach.coach.on_game_start()
                    if stage in ("DOTA_GAMERULES_STATE_GAME_IN_PROGRESS",) and match_start is None:
                        match_start = time.time()
                        log("EVENT: МАТЧ НАЧАЛСЯ (%s)" % g["hero"])
                        notify("Матч начался", "%s — удачи! Напиши мне «что там?» для совета." % g["hero"].replace("npc_dota_hero_", ""))
                        voice_coach.coach.on_game_start()
                    if stage in ("DOTA_GAMERULES_STATE_POST_GAME", "DOTA_GAMERULES_STATE_GAME_OVER") and match_start:
                        dur = int((time.time() - match_start) / 60)
                        log("EVENT: МАТЧ ЗАКОНЧЕН (%s, KDA %s, длился ~%d мин)" % (g["hero"], g["kda"], dur))
                        notify("Матч окончен", "%s, KDA %s, ~%d мин. Напиши мне для разбора!" % (
                            g["hero"].replace("npc_dota_hero_", ""), g["kda"], dur))
                        voice_coach.coach.on_victory()
                        match_start = None
                if g and fresh and g["hero"] != last_hero and g["hero"] != "?":
                    last_hero = g["hero"]
                    log("Герой: %s" % g["hero"])

                # Live Cute Voice Timers (Bounty, Wisdom, River runes)
                if g and fresh and stage == "DOTA_GAMERULES_STATE_GAME_IN_PROGRESS" and isinstance(g.get("clock"), (int, float)):
                    cue = voice_coach.coach.check_timers(int(g["clock"]))
                    if cue:
                        log("EVENT: ОЗВУЧКА -> %s (время матча %d)" % (cue, int(g["clock"])))

                # Auto-Accept match if in menu/queue
                if not (g and fresh and stage in ("DOTA_GAMERULES_STATE_GAME_IN_PROGRESS", "DOTA_GAMERULES_STATE_HERO_SELECTION")):
                    if auto_accept.try_accept_match():
                        log("EVENT: МАТЧ АВТО-ПРИНЯТ!")
                        notify("Dota 2 Auto-Accept", "Матч найден и успешно принят! ✅")
                save_state({"dota_running": True, "gsi_fresh": fresh,
                            "stage": stage if (g and fresh) else None,
                            "hero": (g["hero"] if g else None), "ts": time.time()})
            time.sleep(POLL)
        except KeyboardInterrupt:
            log("watcher остановлен")
            break
        except Exception as e:
            log("ошибка: %s" % e)
            time.sleep(POLL)


if __name__ == "__main__":
    main()
