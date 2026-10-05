"""dota_core часть 1: конфиг, HTTP, GSI. Stdlib-only."""
import json
import os
import time
import urllib.request
import urllib.error

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE, "config.json")
GSI_FILE = os.path.join(BASE, "gsi_latest.json")
COACH_PATH = os.path.join(BASE, "coach_data.json")
HIST_PATH = os.path.join(BASE, "live_history.json")

DEFAULT_CONFIG = {
    "account_id": None,
    "gsi_port": 3000,
    "gsi_host": "127.0.0.1",
    "steam_exe": "C:\\Program Files (x86)\\Steam\\steam.exe",
    "dota_installs": [
        "D:\\SteamLibrary\\steamapps\\common\\dota 2 beta",
        "E:\\SteamLibrary\\steamapps\\common\\dota 2 beta",
    ],
    "opendota_base": "https://api.opendota.com/api",
}


def load_config():
    cfg = dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg.update(json.load(f) or {})
    except FileNotFoundError:
        save_config(cfg)
    except Exception:
        pass
    return cfg


def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def load_coach():
    try:
        with open(COACH_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"timings": [], "pick_advice": {}, "item_guides": {}}


CFG = load_config()
COACH = load_coach()


def http_get_json(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "dota2-mcp/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace")), None
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", "replace")[:400]
        except Exception:
            body = ""
        return None, "HTTP %d: %s" % (e.code, body)
    except Exception as e:
        return None, "сеть: %s" % e


def need_account():
    acc = CFG.get("account_id")
    if not acc:
        return None, ("account_id не задан. Узнай числовой ID на opendota.com "
                      "и вызови dota_set_account.")
    return acc, None


def fmt_match(m):
    hero = m.get("hero_id", "?")
    res = "?"
    if "player_slot" in m and "radiant_win" in m:
        is_rad = m["player_slot"] < 128
        res = "WIN" if (m["radiant_win"] == is_rad) else "LOSS"
    return "%s | hero %s | %d/%d/%d | %s" % (
        m.get("match_id", "?"), hero, m.get("kills", 0),
        m.get("deaths", 0), m.get("assists", 0), res)


def gsi_read():
    try:
        with open(GSI_FILE, encoding="utf-8") as f:
            data = json.load(f)
        age = time.time() - float(data.get("_received_at", 0))
        return data, age, None
    except FileNotFoundError:
        return None, -1, "GSI-данных нет: запусти gsi_server.py и зайди в матч."
    except Exception as e:
        return None, -1, str(e)


def gsi_summary(data, age):
    hero = data.get("hero") or {}
    player = data.get("player") or {}
    mp = data.get("map") or {}
    prov = data.get("provider") or {}
    league = data.get("league") or {}
    buildings = data.get("buildings") or {}
    draft = data.get("draft") or {}
    events = data.get("events") or []
    # spectator detect: hero id 0 / team spectator / player_slot -1
    is_spect = (hero.get("id", 1) in (0, None) or (player.get("team_name") == "spectator")
                or str(hero.get("name", "")) == "")
    out = {
        "возраст_пакета_сек": round(age, 1),
        "герой": hero.get("name", "?"),
        "hp": hero.get("health"), "max_hp": hero.get("max_health"),
        "mp": hero.get("mana"), "max_mp": hero.get("max_mana"),
        "kda": "%s/%s/%s" % (player.get("kills", "?"), player.get("deaths", "?"), player.get("assists", "?")),
        "gpm": player.get("gold_per_min"), "xpm": player.get("xp_per_min"),
        "золото": player.get("gold"),
        "время_сек": mp.get("clock_time", mp.get("game_time", "?")),
        "стадия": mp.get("game_state"),
        "игрок": player.get("name") or prov.get("name"),
    }
    # --- spectator max-info ---
    out["spectator"] = bool(is_spect)
    out["match_id"] = mp.get("matchid")
    out["счёт"] = "%s:%s" % (mp.get("radiant_score", "?"), mp.get("dire_score", "?"))
    out["день"] = mp.get("daytime")
    out["пауза"] = mp.get("paused")
    out["победа"] = mp.get("win_team")
    if league:
        out["лига"] = league.get("name") or league.get("id")
    if draft:
        try:
            out["драфт_ключей"] = len(draft)
            # draft: {"team2": {...}, "team3": {...}, "pick": bool}
            picks = []
            for tk in ("team2", "team3", "2", "3"):
                t = draft.get(tk) or {}
                for k in sorted(t.keys()):
                    v = t[k]
                    if isinstance(v, dict) and v.get("hero_id", 0) > 0:
                        picks.append("%s:%s" % (k, v.get("hero_name") or v.get("hero_id")))
            if picks:
                out["драфт_пики"] = picks[:12]
        except Exception:
            pass
    # buildings: count alive towers per team
    try:
        alive_r = alive_d = 0
        for side in ("radiant", "dire"):
            b = buildings.get(side) or {}
            for k, v in b.items():
                if isinstance(v, dict):
                    hp = v.get("health")
                    if hp is None or (isinstance(hp, int) and hp > 0):
                        alive_r += 1 if side == "radiant" else 0
                        alive_d += 1 if side == "dire" else 0
        if buildings:
            out["здания_жив_radiant"] = alive_r
            out["здания_жив_dire"] = alive_d
    except Exception:
        pass
    # last events human-readable (kills / buybacks / rosh)
    try:
        last = []
        for e in (events or [])[-6:]:
            et = e.get("event_type")
            if et in ("killer", "kill"):
                last.append("kill %s->%s" % (e.get("killer"), e.get("victim")))
            elif et == "generic_event":
                import json as _j
                try:
                    d = _j.loads(e.get("data", "{}"))
                    last.append("%s p%s" % (d.get("type"), d.get("playerid1")))
                except Exception:
                    last.append("event")
            else:
                last.append(str(et))
        if last:
            out["последние_события"] = last
    except Exception:
        pass
    return out


def norm_hero(s):
    return (s or "").strip().lower().replace(" ", "_").replace("-", "_")


# ---------- live-tracker: история снапшотов для дельт/темпа ----------
def _num(v, default=None):
    try:
        if v is None or v == "?":
            return default
        return float(v)
    except Exception:
        return default


def snap_point(data):
    """Плоский снапшот из GSI для истории. Stdlib-only."""
    mp = data.get("map") or {}
    pl = data.get("player") or {}
    hero = data.get("hero") or {}
    bld = data.get("buildings") or {}
    alive_r = alive_d = 0
    try:
        for side in ("radiant", "dire"):
            b = bld.get(side) or {}
            for _, v in b.items():
                if isinstance(v, dict):
                    hp = v.get("health")
                    if hp is None or (isinstance(hp, (int, float)) and hp > 0):
                        if side == "radiant":
                            alive_r += 1
                        else:
                            alive_d += 1
    except Exception:
        pass
    ct = mp.get("clock_time", mp.get("game_time"))
    return {
        "t": time.time(),
        "game_time": _num(ct, 0) or 0,
        "matchid": str(mp.get("matchid") or "0"),
        "stage": mp.get("game_state"),
        "radiant_score": _num(mp.get("radiant_score"), 0) or 0,
        "dire_score": _num(mp.get("dire_score"), 0) or 0,
        "gold": _num(pl.get("gold"), None),
        "gpm_gsi": _num(pl.get("gold_per_min"), None),
        "xpm_gsi": _num(pl.get("xp_per_min"), None),
        "kills": _num(pl.get("kills"), None),
        "deaths": _num(pl.get("deaths"), None),
        "assists": _num(pl.get("assists"), None),
        "lh": _num(pl.get("last_hits"), None),
        "denies": _num(pl.get("denies"), None),
        "hp": _num(hero.get("health"), None),
        "max_hp": _num(hero.get("max_health"), None),
        "mp": _num(hero.get("mana"), None),
        "max_mp": _num(hero.get("max_mana"), None),
        "alive": hero.get("alive"),
        "respawn": _num(hero.get("respawn_seconds"), None),
        "buyback_cost": _num(hero.get("buyback_cost"), None),
        "buyback_cd": _num(hero.get("buyback_cooldown"), None),
        "level": _num((data.get("abilities") or {}).get("level"), None),
        "buildings_r": alive_r,
        "buildings_d": alive_d,
        "events_n": len(data.get("events") or []),
    }


def load_hist():
    try:
        with open(HIST_PATH, encoding="utf-8") as f:
            h = json.load(f) or []
        return h if isinstance(h, list) else []
    except Exception:
        return []


def save_hist(h):
    try:
        h = (h or [])[-720:]  # ~1 час при опросе каждые 5 сек
        with open(HIST_PATH, "w", encoding="utf-8") as f:
            json.dump(h, f, ensure_ascii=False)
    except Exception:
        pass


def track_tick(max_age_min=60):
    """Добавить текущий GSI-снапшот в историю, вернуть (hist, cur). Чистит при смене матча."""
    data, age, err = gsi_read()
    if data is None:
        return load_hist(), None, err
    cur = snap_point(data)
    cur["_fresh"] = age < 15
    h = load_hist()
    if h and cur["matchid"] not in ("0", "", None):
        # смена матча -> резать историю
        lasts = [p for p in h if p.get("matchid") not in ("0", "", None)]
        if lasts and lasts[-1].get("matchid") != cur["matchid"]:
            h = []
    h.append(cur)
    # чистим старье
    now = time.time()
    h = [p for p in h if now - float(p.get("t", now)) < max_age_min * 60][-720:]
    save_hist(h)
    return h, cur, None


def _at_or_before(h, seconds_ago):
    if not h:
        return None
    target = time.time() - seconds_ago
    best = None
    for p in h:
        if float(p.get("t", 0)) <= target:
            best = p
    return best or h[0]


def _rate(new, old, dt_min):
    if new is None or old is None or not dt_min or dt_min <= 0:
        return None
    try:
        return round((float(new) - float(old)) / dt_min, 1)
    except Exception:
        return None


def deltas(h, windows=(60, 300)):
    """Дельты золота/счёта/LH/киллов за окна в секундах. Возвращает dict."""
    if not h:
        return {}
    cur = h[-1]
    out = {}
    for w in windows:
        base = _at_or_before(h, w)
        if not base:
            continue
        dt = (float(cur.get("t", 0)) - float(base.get("t", 0))) / 60.0
        if dt < 0.05:
            continue
        tag = "%dсек" % w if w < 120 else "%dмин" % (w // 60)
        d = {}
        g = _rate(cur.get("gold"), base.get("gold"), dt)
        if g is not None:
            d["золото_дельта"] = round(float(cur["gold"]) - float(base["gold"]))
            d["золото_в_мин_факт"] = g  # реальный темп, не GSI gpm
        for k in ("kills", "deaths", "assists", "lh", "denies", "radiant_score", "dire_score"):
            if cur.get(k) is not None and base.get(k) is not None:
                dd = float(cur[k]) - float(base[k])
                if dd:
                    d[k + "_дельта"] = int(dd) if dd == int(dd) else round(dd, 1)
        lh_rate = _rate(cur.get("lh"), base.get("lh"), dt)
        if lh_rate is not None:
            d["lh_в_мин_факт"] = lh_rate
        # здания потеряны за окно
        for k in ("buildings_r", "buildings_d"):
            if cur.get(k) is not None and base.get(k) is not None:
                dd = float(cur[k]) - float(base[k])
                if dd:
                    d[k + "_дельта"] = int(dd)
        out[tag] = d
    # сравнение факта vs GSI gpm/xpm
    try:
        f1 = (out.get("5мин") or out.get("60сек") or {})
        fg = f1.get("золото_в_мин_факт")
        if fg is not None and cur.get("gpm_gsi") is not None:
            out["gpm_gsi_сейчас"] = cur.get("gpm_gsi")
            out["gpm_факт_vs_gsi"] = round(float(fg) - float(cur["gpm_gsi"]), 1)
    except Exception:
        pass
    return out
