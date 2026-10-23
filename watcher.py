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
    print(line, flush=True)
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
                        "-Command", ps], capture_output=True, timeout=15)
    except Exception:
        pass


def dota_running():
    try:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq dota2.exe", "/FO", "CSV", "/NH"],
                             capture_output=True, timeout=10)
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


def main():
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
            elif running != was_running:
                was_running = running
                if running:
                    log("EVENT: Dota 2 ЗАПУЩЕНА")
                    notify("Dota 2 MCP", "Дота запущена. Слежу за матчем.")
                else:
                    log("EVENT: Dota 2 ЗАКРЫТА")
                    notify("Dota 2 MCP", "Дота закрыта.")
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
                    if stage in ("DOTA_GAMERULES_STATE_GAME_IN_PROGRESS",) and match_start is None:
                        match_start = time.time()
                        log("EVENT: МАТЧ НАЧАЛСЯ (%s)" % g["hero"])
                        notify("Матч начался", "%s — удачи! Напиши мне «что там?» для совета." % g["hero"].replace("npc_dota_hero_", ""))
                    if stage in ("DOTA_GAMERULES_STATE_POST_GAME", "DOTA_GAMERULES_STATE_GAME_OVER") and match_start:
                        dur = int((time.time() - match_start) / 60)
                        log("EVENT: МАТЧ ЗАКОНЧЕН (%s, KDA %s, длился ~%d мин)" % (g["hero"], g["kda"], dur))
                        notify("Матч окончен", "%s, KDA %s, ~%d мин. Напиши мне для разбора!" % (
                            g["hero"].replace("npc_dota_hero_", ""), g["kda"], dur))
                        match_start = None
                if g and fresh and g["hero"] != last_hero and g["hero"] != "?":
                    last_hero = g["hero"]
                    log("Герой: %s" % g["hero"])
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
