"""Live-доска ч.1: данные. Импортируется из live_board_server."""
import json
import os
import sys
import threading
import time

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import dota_core as C

HEROES = {}
try:
    with open(os.path.join(BASE, "heroes_cache.json"), encoding="utf-8") as f:
        for h in json.load(f) or []:
            HEROES[int(h.get("id"))] = h.get("localized_name", str(h.get("id")))
except Exception:
    pass

_CACHE = {"board": None, "ts": 0.0}
_LOCK = threading.Lock()


def hero_name(hid):
    try:
        return HEROES.get(int(hid), "hero_%s" % hid)
    except Exception:
        return str(hid)


def build_board():
    data, age, err = C.gsi_read()
    h = C.load_hist()
    tempo = C.deltas(h) if h else {}
    board = {"ok": True, "now": time.strftime("%H:%M:%S"),
             "gsi_age_sec": round(age, 1) if age >= 0 else -1,
             "history_points": len(h), "tempo": tempo}
    if data is None:
        board["ok"] = False
        board["error"] = err
        return board
    mp = data.get("map") or {}
    pl = data.get("player") or {}
    ev = data.get("events") or []
    mid = str(mp.get("matchid") or "0")
    board["match_id"] = mid
    board["stage"] = mp.get("game_state")
    board["clock"] = mp.get("clock_time", mp.get("game_time"))
    board["score"] = {"radiant": mp.get("radiant_score"), "dire": mp.get("dire_score")}
    board["paused"] = mp.get("paused")
    board["win_team"] = mp.get("win_team")
    board["daytime"] = mp.get("daytime")
    is_s = pl.get("team_name") == "spectator" or (data.get("hero") or {}).get("id", 1) in (0, None)
    board["spectator"] = bool(is_s)
    board["you"] = {"name": pl.get("name"), "team": pl.get("team_name"), "gold": pl.get("gold"),
                    "kda": "%s/%s/%s" % (pl.get("kills", "?"), pl.get("deaths", "?"), pl.get("assists", "?")),
                    "lh": pl.get("last_hits"), "denies": pl.get("denies"),
                    "gpm_gsi": pl.get("gold_per_min"), "xpm": pl.get("xp_per_min")}
    last = []
    for e in ev[-8:]:
        try:
            if e.get("event_type") == "generic_event":
                d = json.loads(e.get("data", "{}"))
                last.append("%s p%s (%sс)" % (d.get("type"), d.get("playerid1"), e.get("game_time")))
            else:
                last.append("%s (%sс)" % (e.get("event_type"), e.get("game_time")))
        except Exception:
            pass
    board["events"] = last[-8:]
    players = []
    src = "gsi-only"
    if mid not in ("0", "", None):
        live, _ = C.http_get_json("%s/live" % C.CFG.get("opendota_base"), timeout=10)
        found = None
        try:
            for m in live or []:
                if str(m.get("match_id")) == mid:
                    found = m
                    break
        except Exception:
            pass
        if found:
            src = "opendota-live"
            board["live_meta"] = {"avg_mmr": found.get("average_mmr"), "delay": found.get("delay"),
                                  "spectators": found.get("spectators"),
                                  "radiant_lead": found.get("radiant_lead")}
            for p in found.get("players") or []:
                players.append({"account_id": p.get("account_id"), "hero": hero_name(p.get("hero_id")),
                                "hero_id": p.get("hero_id"),
                                "team": "radiant" if p.get("team") == 0 else "dire",
                                "slot": p.get("team_slot")})
        else:
            det, _ = C.http_get_json("%s/matches/%s" % (C.CFG.get("opendota_base"), mid), timeout=15)
            if det and det.get("players"):
                src = "opendota-match"
                for p in det.get("players") or []:
                    slot = p.get("player_slot", 0) or 0
                    players.append({"account_id": p.get("account_id"), "hero": hero_name(p.get("hero_id")),
                                    "hero_id": p.get("hero_id"),
                                    "team": "radiant" if slot < 128 else "dire",
                                    "kda": "%s/%s/%s" % (p.get("kills", 0), p.get("deaths", 0), p.get("assists", 0)),
                                    "gpm": p.get("gold_per_min"), "xpm": p.get("xp_per_min"),
                                    "lh": p.get("last_hits"), "denies": p.get("denies"),
                                    "gold": p.get("total_gold"), "hero_damage": p.get("hero_damage"),
                                    "tower_damage": p.get("tower_damage"), "level": p.get("level")})
                board["match_meta"] = {"duration_min": round((det.get("duration") or 0) / 60.0, 1),
                                       "radiant_win": det.get("radiant_win")}
    board["players_src"] = src
    board["players"] = players
    return board


def get_board():
    with _LOCK:
        if time.time() - _CACHE["ts"] < 4 and _CACHE["board"]:
            return _CACHE["board"]
    b = build_board()
    with _LOCK:
        _CACHE["board"] = b
        _CACHE["ts"] = time.time()
    return b
