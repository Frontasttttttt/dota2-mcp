"""Live-доска ч.1: данные. Импортируется из live_board_server. Stdlib-only."""
import json
import os
import sys
import threading
import time

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import dota_core as C
import auto_scout

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


def compute_map_timers(clock_sec):
    """Вычисляет таймеры карты по актуальным правилам Dota 2:
    - Баунти руны: с 00:00 и каждые 4 минуты (240 сек)
    - Лотусы: каждые 3 минуты (180 сек)
    - Руны воды: 02:00 и 04:00 (обе точки реки)
    - Активные руны реки (Щит, Хаста, Иллюзии, ДД, Инвиз, Реген, Аркана): с 06:00 каждые 2 мин (120 сек)
    - Руны мудрости: каждые 7 минут (420 сек)
    - Смена дня/ночи и логово Рошана: каждые 5 минут (300 сек)
    - Терзатель: 20:00 (1200 сек)
    """
    if clock_sec is None or clock_sec < 0:
        return {
            "bounty_sec": 240, "bounty_fmt": "04:00",
            "river_sec": 120, "river_fmt": "02:00", "river_type": "Руны воды (02:00, 04:00)",
            "lotus_sec": 180, "lotus_fmt": "03:00",
            "wisdom_sec": 420, "wisdom_fmt": "07:00",
            "roshan_cave": "Юго-Восток (Radiant ☀️)",
            "roshan_fmt": "05:00",
            "roshan_status": "Юго-Восток (Radiant ☀️)",
            "tormentor_sec": 1200, "tormentor_fmt": "20:00", "tormentor_status": "Спавн в 20:00",
            "is_day": True, "day_night_sec": 300, "day_night_fmt": "05:00"
        }

    c = int(clock_sec)

    # 1. Баунти руны: каждые 4 мин (240 сек)
    bounty_rem = 240 - (c % 240) if c >= 0 else 0
    bounty_fmt = "%02d:%02d" % (bounty_rem // 60, bounty_rem % 60)

    # 2. Лотусы: каждые 3 мин (180 сек)
    lotus_rem = 180 - (c % 180) if c >= 0 else 0
    lotus_fmt = "%02d:%02d" % (lotus_rem // 60, lotus_rem % 60)

    # 3. Руны реки: Вода на 2:00 (120s) и 4:00 (240s). Активные руны с 6:00 (360s) каждые 2 мин (120s)
    if c < 120:
        river_rem = 120 - c
        river_type = "Руны воды (обе точки)"
    elif c < 240:
        river_rem = 240 - c
        river_type = "Руны воды (обе точки)"
    elif c < 360:
        river_rem = 360 - c
        river_type = "Первые активные руны реки"
    else:
        river_rem = 120 - (c % 120)
        river_type = "Активная руна реки (каждые 2 мин)"
    river_fmt = "%02d:%02d" % (river_rem // 60, river_rem % 60)

    # 4. Руны мудрости: каждые 7 мин (420 сек)
    wisdom_rem = 420 - (c % 420) if c >= 0 else 0
    wisdom_fmt = "%02d:%02d" % (wisdom_rem // 60, wisdom_rem % 60)

    # 5. Смена дня и ночи + Рошан: каждые 5 мин (300 сек).
    # День: 0-5, 10-15... Рошан в Юго-Восточном логове (Radiant)
    # Ночь: 5-10, 15-20... Рошан в Северо-Западном логове (Dire)
    cycle = c // 300
    is_day = (cycle % 2 == 0)
    day_rem = 300 - (c % 300)
    day_fmt = "%02d:%02d" % (day_rem // 60, day_rem % 60)
    roshan_current_cave = "Юго-Восток (Radiant ☀️)" if is_day else "Северо-Запад (Dire 🌙)"
    roshan_next_cave = "Dire 🌙" if is_day else "Radiant ☀️"
    roshan_status = "%s (переход через %s в %s)" % (roshan_current_cave, day_fmt, roshan_next_cave)

    # 6. Терзатель: спавн на 20:00 (1200 сек)
    if c < 1200:
        tormentor_rem = 1200 - c
        tormentor_fmt = "%02d:%02d" % (tormentor_rem // 60, tormentor_rem % 60)
        tormentor_status = "Спавн через %s" % tormentor_fmt
    else:
        tormentor_rem = 0
        tormentor_fmt = "Активен"
        tormentor_status = "Активен (осколок Аганима)"

    return {
        "clock_sec": c,
        "bounty_sec": bounty_rem,
        "bounty_fmt": bounty_fmt,
        "river_sec": river_rem,
        "river_fmt": river_fmt,
        "river_type": river_type,
        "lotus_sec": lotus_rem,
        "lotus_fmt": lotus_fmt,
        "wisdom_sec": wisdom_rem,
        "wisdom_fmt": wisdom_fmt,
        "is_day": is_day,
        "day_night_sec": day_rem,
        "day_night_fmt": day_fmt,
        "roshan_cave": roshan_current_cave,
        "roshan_fmt": day_fmt,
        "roshan_status": roshan_status,
        "tormentor_sec": tormentor_rem,
        "tormentor_fmt": tormentor_fmt,
        "tormentor_status": tormentor_status,
    }


def parse_buildings(bld_data):
    """Парсит состояние вышек и бараков для Radiant и Dire."""
    out = {
        "radiant": {"towers_alive": 0, "rax_alive": 0, "ancient_alive": True, "details": {}},
        "dire": {"towers_alive": 0, "rax_alive": 0, "ancient_alive": True, "details": {}},
    }
    if not isinstance(bld_data, dict):
        return out

    for team in ("radiant", "dire"):
        team_bld = bld_data.get(team) or {}
        for b_name, b_val in team_bld.items():
            if isinstance(b_val, dict):
                hp = b_val.get("health", 0)
                alive = hp > 0
                out[team]["details"][b_name] = alive
                if "tower" in b_name:
                    if alive:
                        out[team]["towers_alive"] += 1
                elif "rax" in b_name:
                    if alive:
                        out[team]["rax_alive"] += 1
                elif "fort" in b_name:
                    out[team]["ancient_alive"] = alive
    return out


def build_board():
    data, age, err = C.gsi_read()
    h = C.load_hist()
    tempo = C.deltas(h) if h else {}
    board = {
        "ok": True,
        "now": time.strftime("%H:%M:%S"),
        "gsi_age_sec": round(age, 1) if age >= 0 else -1,
        "history_points": len(h),
        "tempo": tempo,
    }
    if data is None:
        board["ok"] = False
        board["error"] = err
        return board

    mp = data.get("map") or {}
    pl = data.get("player") or {}
    hero = data.get("hero") or {}
    ev = data.get("events") or []
    bld = data.get("buildings") or {}

    mid = str(mp.get("matchid") or "0")
    board["match_id"] = mid
    board["stage"] = mp.get("game_state", "UNKNOWN")
    raw_clock = mp.get("clock_time", mp.get("game_time", 0))
    board["clock"] = raw_clock
    board["timers"] = compute_map_timers(raw_clock)
    board["buildings"] = parse_buildings(bld)
    board["score"] = {"radiant": mp.get("radiant_score", 0), "dire": mp.get("dire_score", 0)}
    board["paused"] = mp.get("paused", False)
    board["win_team"] = mp.get("win_team", "none")
    board["daytime"] = mp.get("daytime", True)

    is_s = pl.get("team_name") == "spectator" or hero.get("id", 1) in (0, None)
    board["spectator"] = bool(is_s)

    # Личные данные игрока
    h_name_raw = hero.get("name", "")
    h_name_clean = h_name_raw.replace("npc_dota_hero_", "").replace("_", " ").title() if h_name_raw else "Hero"
    gold = pl.get("gold", 0) or 0
    bb_cost = hero.get("buyback_cost", 0) or 0
    bb_cd = hero.get("buyback_cooldown", 0) or 0
    can_bb = (gold >= bb_cost) and (bb_cd == 0)

    board["you"] = {
        "name": pl.get("name", "Player"),
        "hero_name": h_name_clean,
        "team": pl.get("team_name", "unknown"),
        "gold": gold,
        "kda": "%s/%s/%s" % (pl.get("kills", 0), pl.get("deaths", 0), pl.get("assists", 0)),
        "lh": pl.get("last_hits", 0),
        "denies": pl.get("denies", 0),
        "gpm_gsi": pl.get("gold_per_min", 0),
        "xpm_gsi": pl.get("xp_per_min", 0),
        "level": hero.get("level", 1),
        "alive": hero.get("alive", True),
        "respawn_seconds": hero.get("respawn_seconds", 0),
        "health": hero.get("health", 0),
        "max_health": hero.get("max_health", 1),
        "mana": hero.get("mana", 0),
        "max_mana": hero.get("max_mana", 1),
        "buyback_cost": bb_cost,
        "buyback_cooldown": bb_cd,
        "has_buyback": can_bb,
    }

    # Последние события
    last = []
    for e in ev[-10:]:
        try:
            et = e.get("event_type")
            gt = e.get("game_time", 0)
            fmt_t = "%02d:%02d" % (int(gt) // 60, int(gt) % 60) if gt else "--:--"
            if et in ("killer", "kill"):
                last.append("⚔️ [%s] %s убил %s" % (fmt_t, e.get("killer"), e.get("victim")))
            elif et == "roshan_killed":
                last.append("🐉 [%s] Рошан повержен!" % fmt_t)
            elif et == "generic_event":
                d = json.loads(e.get("data", "{}"))
                tp = d.get("type", "событие")
                last.append("⚡ [%s] %s" % (fmt_t, tp))
            else:
                last.append("📢 [%s] %s" % (fmt_t, et))
        except Exception:
            pass
    board["events"] = last[-8:] if last else ["Матч идёт, событий пока нет"]

    # Автоматическая разведка лобби и смурф-радар (GSI + OpenDota Live + Console)
    scout_mgr = auto_scout.get_scout_manager()
    scout_mgr.update_from_gsi(data)
    lobby_state = scout_mgr.get_lobby_state()
    board["lobby_scout"] = lobby_state

    # Игроки для обратной совместимости
    players = []
    for team_key in ("radiant", "dire", "unassigned"):
        for p in lobby_state.get(team_key, []):
            players.append({
                "account_id": p.get("account_id"),
                "name": p.get("name"),
                "hero": p.get("hero_name") or hero_name(p.get("hero_id")),
                "hero_id": p.get("hero_id"),
                "team": p.get("team"),
                "slot": p.get("slot"),
            })

    board["players_src"] = "auto_scout"
    board["players"] = players
    return board


def get_board():
    with _LOCK:
        if time.time() - _CACHE["ts"] < 1.5 and _CACHE["board"]:
            return _CACHE["board"]
    b = build_board()
    with _LOCK:
        _CACHE["board"] = b
        _CACHE["ts"] = time.time()
    return b
