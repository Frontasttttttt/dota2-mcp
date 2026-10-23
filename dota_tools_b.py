"""Инструменты ч.2: матчи, тренер, STRATZ. Stdlib-only."""
import json
import os
import urllib.request
import urllib.error
import dota_core as C


def t_recent_matches(limit=10):
    acc, err = C.need_account()
    if err:
        return {"ok": False, "error": err}
    try:
        limit = max(1, min(int(limit), 30))
    except Exception:
        limit = 10
    data, e = C.http_get_json("%s/players/%s/recentMatches" % (C.CFG.get("opendota_base"), acc))
    if e:
        return {"ok": False, "error": "OpenDota: %s" % e}
    return {"ok": True, "матчи": [C.fmt_match(m) for m in (data or [])[:limit]]}


def t_match_details(match_id):
    import postgame_analyzer
    aid = C.CFG.get("account_id")
    rep = postgame_analyzer.analyze_match(match_id, aid)
    if rep.get("ok"):
        rep["текст"] = postgame_analyzer.fmt_postgame_report(rep)
    return rep


def t_hero_stats(hero_id):
    acc, err = C.need_account()
    if err:
        return {"ok": False, "error": err}
    heroes, e = C.http_get_json("%s/players/%s/heroes" % (C.CFG.get("opendota_base"), acc))
    if e:
        return {"ok": False, "error": "OpenDota: %s" % e}
    try:
        hid = int(hero_id)
    except Exception:
        return {"ok": False, "error": "hero_id числом"}
    for h in heroes or []:
        if h.get("hero_id") == hid:
            g, w = h.get("games", 0), h.get("win", 0)
            return {"ok": True, "hero_id": hid, "игры": g, "победы": w,
                    "винрейт": round(100.0 * w / g, 1) if g else 0}
    return {"ok": True, "hero_id": hid, "игры": 0}


def t_coach_tip(hero=None, minute=None):
    data = None
    if minute is None:
        data, _, _ = C.gsi_read()
        if data is not None:
            mp = data.get("map") or {}
            try:
                minute = int(float(mp.get("clock_time", mp.get("game_time", 0))) // 60)
            except Exception:
                minute = None
            if hero is None:
                h = (data.get("hero") or {}).get("name", "")
                if h.startswith("npc_dota_hero_"):
                    hero = h[len("npc_dota_hero_"):]
    spect_extra = []
    if data is not None:
        pl = data.get("player") or {}
        if pl.get("team_name") == "spectator" or (data.get("hero") or {}).get("id", 1) in (0, None):
            mp = data.get("map") or {}
            spect_extra.append("Наблюдение: матч %s, счёт %s:%s, время %s, стадия %s." % (
                mp.get("matchid"), mp.get("radiant_score"), mp.get("dire_score"),
                mp.get("clock_time", mp.get("game_time")), mp.get("game_state")))
            for e in (data.get("events") or [])[-3:]:
                try:
                    import json as _j
                    dd = _j.loads(e.get("data", "{}")) if e.get("event_type") == "generic_event" else {}
                    if dd:
                        spect_extra.append("Событие: %s (p%s)" % (dd.get("type"), dd.get("playerid1")))
                except Exception:
                    pass
    tips = []
    if minute is not None:
        best = None
        for t in C.COACH.get("timings", []):
            if t.get("min", 0) <= int(minute):
                best = t
        if best:
            tips.append("Минута ~%s: %s" % (minute, best["text"]))
    if hero:
        g = (C.COACH.get("item_guides") or {}).get(C.norm_hero(hero))
        if g:
            tips.append("Закуп %s: старт [%s]; мид [%s]; лейт [%s]." % (
                hero, ", ".join(g.get("starting", [])), ", ".join(g.get("mid", [])), ", ".join(g.get("late", []))))
    if not tips:
        tips = ["Фарми, носи TP, смотри миникарту.", "Варды 2/6 мин, wisdom 7/14 мин, BKB к 25-30 мин."]
    return {"ok": True, "советы": spect_extra + tips}


def t_live_tick():
    """Один тик живого трекера: снапшот + дельты за 1 и 5 мин + summary. Для watch/live."""
    h, cur, err = C.track_tick()
    if cur is None:
        return {"ok": False, "error": err or "нет GSI"}
    data, age, _ = C.gsi_read()
    out = {"ok": True, "fresh": bool(cur.get("_fresh")), "точек_в_истории": len(h),
           "summary": C.gsi_summary(data, age) if data else cur,
           "сейчас": {k: cur.get(k) for k in ("game_time", "gold", "gpm_gsi", "xpm_gsi", "kills", "deaths",
                                              "assists", "lh", "denies", "level", "hp", "max_hp", "alive",
                                              "respawn", "buyback_cost", "radiant_score", "dire_score")},
           "темп": C.deltas(h)}
    try:
        t5 = (out["темп"].get("5мин") or {})
        fg = t5.get("золото_в_мин_факт")
        if fg is not None:
            if fg < 250:
                out["вердикт"] = "Темп низкий (%.0f золота/мин за 5 мин): жмёшься, иди фармить стаки/лес." % fg
            elif fg > 550:
                out["вердикт"] = "Темп отличный (%.0f/мин): дави, забирай вышку/рошана." % fg
    except Exception:
        pass
    return out


def t_spectate_live():
    """Максимум инфы при просмотре друга: GSI + OpenDota live + разбор матча."""
    data, age, err = C.gsi_read()
    if data is None:
        return {"ok": False, "error": err}
    mp = data.get("map") or {}
    mid = mp.get("matchid")
    out = {"ok": True, "summary": C.gsi_summary(data, age)}
    if not mid or str(mid) == "0":
        out["opendota"] = "matchid нет в GSI (меню/лобби). Открой просмотр матча — GSI пришлёт matchid."
        return out
    base = C.CFG.get("opendota_base")
    live, _ = C.http_get_json("%s/live" % base, timeout=10)
    found = None
    try:
        for m in live or []:
            if str(m.get("match_id")) == str(mid):
                found = m
                break
    except Exception:
        pass
    if found:
        out["live"] = {"match_id": found.get("match_id"),
                       "счёт": "%s:%s" % (found.get("radiant_score"), found.get("dire_score")),
                       "время": found.get("game_time"),
                       "лига": (found.get("league") or {}).get("name"),
                       "игроки": [{"hero": p.get("hero_id"), "kda": "%s/%s/%s" % (p.get("kills"), p.get("deaths"), p.get("assists")),
                                   "gpm": p.get("gold_per_min"), "xpm": p.get("xp_per_min"),
                                   "net": p.get("gold")} for p in (found.get("players") or [])]}
    else:
        out["live"] = "матч %s не в топ-live OpenDota (обычно там только про/хай-MMR). GSI-данные выше — основной источник." % mid
    det = t_match_details(mid)
    if det.get("ok"):
        out["разбор_opendota"] = det
    return out


def t_pick_advice(enemies):
    import draft_engine
    res = draft_engine.get_draft_advice(enemies)
    if res.get("ok"):
        res["текст"] = draft_engine.fmt_draft_advice(res)
    return res


def t_item_guide(hero):
    guides = C.COACH.get("item_guides") or {}
    return {"ok": True, "герой": hero or "общий",
            "билд": guides.get(C.norm_hero(hero), guides.get("default"))}


def t_stratz_match(match_id):
    token = os.environ.get("STRATZ_TOKEN", "")
    if not token:
        return {"ok": False, "error": "Нужен STRATZ_TOKEN (stratz.com/api)."}
    try:
        mid = int(match_id)
    except Exception:
        return {"ok": False, "error": "match_id числом"}
    q = "query($id: Long!) { match(id: $id) { id didRadiantWin players { heroId kills deaths assists } } }"
    body = json.dumps({"query": q, "variables": {"id": mid}}).encode("utf-8")
    req = urllib.request.Request("https://api.stratz.com/graphql", data=body,
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": "STRATZ HTTP %d" % e.code}
    except Exception as e:
        return {"ok": False, "error": "сеть: %s" % e}
    m = (data.get("data") or {}).get("match")
    if not m:
        return {"ok": False, "error": "матч не найден"}
    return {"ok": True, "match_id": m.get("id"), "победа_radiant": m.get("didRadiantWin"),
            "игроки": [{"hero": p.get("heroId"),
                        "kda": "%s/%s/%s" % (p.get("kills"), p.get("deaths"), p.get("assists"))}
                       for p in (m.get("players") or [])]}



def t_scout_player(account_id):
    import scout_engine
    res = scout_engine.scout_player(account_id)
    if res.get("ok"):
        res["текст"] = scout_engine.fmt_player_scout(res)
    return res


def t_scout_lobby(players=None):
    import auto_scout
    import scout_engine

    if not players or str(players).strip().lower() in ("auto", "live", "current"):
        mgr = auto_scout.get_scout_manager()
        st = mgr.get_lobby_state()
        if st.get("total_players", 0) > 0:
            st["текст"] = mgr.fmt_lobby_report()
            return st
        # Если лобби пока пустое, но есть сохраненный аккаунт — покажем его
        aid = C.CFG.get("account_id")
        if aid:
            res = scout_engine.scout_lobby(str(aid))
            if res.get("ok"):
                res["текст"] = "ℹ️ Активное лобби пока пустое (ожидание драфта). Твой профиль:\n" + scout_engine.fmt_lobby_report(res)
            return res
        return {"ok": False, "error": "Лобби не обнаружено. Зайди в матч или передай ID: scout 12345678"}

    res = scout_engine.scout_lobby(players)
    if res.get("ok"):
        res["текст"] = scout_engine.fmt_lobby_report(res)
    return res
