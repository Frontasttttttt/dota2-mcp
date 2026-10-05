"""Инструменты ч.1: запуск, GSI, аккаунт, OpenDota-профиль."""
import os
import subprocess
import dota_core as C


def t_launch(mode="normal", hero=None):
    steam = C.CFG.get("steam_exe")
    if not steam or not os.path.exists(steam):
        for c in ["C:\\Program Files (x86)\\Steam\\steam.exe", "C:\\Program Files\\Steam\\steam.exe"]:
            if os.path.exists(c):
                steam = c
                break
    try:
        subprocess.Popen([steam, "-applaunch", "570"])
        msg = "Dota 2 запускается через Steam."
    except Exception as e:
        return {"ok": False, "error": "не смог запустить Steam: %s" % e}
    if mode == "training":
        msg += " Тренировка: Играть -> Тренировка с ботами -> сложность -> Начать."
    elif hero:
        msg += " Потренируй %s в лобби с ботами или демо." % hero
    return {"ok": True, "message": msg}


def t_gsi_status():
    data, age, err = C.gsi_read()
    if data is None:
        return {"ok": False, "hint": err}
    return {"ok": True, "last_packet_age_sec": round(age, 1), "fresh": age < 5}


def t_gsi_latest():
    data, age, err = C.gsi_read()
    if data is None:
        return {"ok": False, "error": err}
    return {"ok": True, "summary": C.gsi_summary(data, age), "raw_keys": sorted(data.keys())}


def t_gsi_install():
    import sys
    sys.path.insert(0, os.path.join(C.BASE, "tools"))
    import install_gsi
    port = int(C.CFG.get("gsi_port", 3000))
    done, failed = [], []
    for root in C.CFG.get("dota_installs") or []:
        if not os.path.exists(root):
            failed.append("%s (нет папки)" % root)
            continue
        try:
            done.append(install_gsi.install_to(root, port))
        except Exception as e:
            failed.append("%s: %s" % (root, e))
    return {"ok": bool(done), "installed": done, "failed": failed}


def t_set_account(account_id):
    try:
        acc = int(account_id)
    except Exception:
        return {"ok": False, "error": "account_id должен быть числом"}
    C.CFG["account_id"] = acc
    C.save_config(C.CFG)
    return {"ok": True, "account_id": acc}


def t_profile():
    acc, err = C.need_account()
    if err:
        return {"ok": False, "error": err}
    base = C.CFG.get("opendota_base")
    prof, e1 = C.http_get_json("%s/players/%s" % (base, acc))
    wl, _ = C.http_get_json("%s/players/%s/wl" % (base, acc))
    heroes, _ = C.http_get_json("%s/players/%s/heroes" % (base, acc))
    if e1 and not prof:
        return {"ok": False, "error": "OpenDota: %s" % e1}
    out = {"ok": True, "account_id": acc}
    if prof:
        out["ник"] = (prof.get("profile") or {}).get("personaname")
        out["mmr_оценка"] = (prof.get("mmr_estimate") or {}).get("estimate")
    if wl:
        w, l = wl.get("win", 0), wl.get("lose", 0)
        out["победы"] = w
        out["поражения"] = l
        out["винрейт"] = round(100.0 * w / (w + l), 1) if (w + l) else 0
    if heroes:
        top = sorted(heroes, key=lambda h: h.get("games", 0), reverse=True)[:5]
        out["топ_герои"] = [{"hero_id": h.get("hero_id"), "игры": h.get("games"), "победы": h.get("win")} for h in top]
    return out
