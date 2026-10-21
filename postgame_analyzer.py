"""postgame_analyzer.py — Глубокий алгоритмический разбор матчей Dota 2.
100% бесплатно: OpenDota API + локальный кэш артефактов + чистая математика (0 платных токенов).
"""
import io
import json
import os
import sys
import time
import urllib.request
import urllib.error

BASE = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE, "cache")
ITEMS_CACHE_FILE = os.path.join(CACHE_DIR, "items.json")
HEROES_FILE = os.path.join(BASE, "heroes_cache.json")

os.makedirs(CACHE_DIR, exist_ok=True)

# Загрузка базы героев
HEROES_MAP = {}
try:
    with open(HEROES_FILE, encoding="utf-8") as f:
        for h in json.load(f) or []:
            HEROES_MAP[int(h["id"])] = h.get("localized_name", str(h["id"]))
except Exception:
    pass


def _http_get(url, timeout=15):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace")), None
    except urllib.error.HTTPError as e:
        return None, "HTTP %d" % e.code
    except Exception as e:
        return None, str(e)


# ----------------- Кэш констант предметов -----------------
def load_items_constants():
    if os.path.exists(ITEMS_CACHE_FILE):
        try:
            with open(ITEMS_CACHE_FILE, encoding="utf-8") as f:
                data = json.load(f)
                if data and time.time() - os.path.getmtime(ITEMS_CACHE_FILE) < 86400 * 7:  # 7 дней
                    return {int(v["id"]): v.get("dname", k) for k, v in data.items() if "id" in v}
        except Exception:
            pass

    data, err = _http_get("https://api.opendota.com/api/constants/items")
    if data:
        try:
            with open(ITEMS_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            return {int(v["id"]): v.get("dname", k) for k, v in data.items() if "id" in v}
        except Exception:
            pass
    return {}


ITEMS_MAP = load_items_constants()


def get_item_name(item_id):
    if not item_id or item_id == 0:
        return None
    return ITEMS_MAP.get(int(item_id), "Item_%d" % item_id)


def analyze_match(match_id, target_account_id=None):
    """Глубокий алгоритмический разбор матча."""
    try:
        mid = int(match_id)
    except Exception:
        return {"ok": False, "error": "match_id должен быть числом"}

    url = "https://api.opendota.com/api/matches/%d" % mid
    data, err = _http_get(url)
    if not data or err:
        return {"ok": False, "error": "Не удалось загрузить матч из OpenDota: %s" % (err or "пустой ответ")}

    dur_sec = data.get("duration", 0) or 0
    dur_min = round(dur_sec / 60.0, 1)
    rad_win = bool(data.get("radiant_win"))
    rad_score = data.get("radiant_score", 0) or 0
    dire_score = data.get("dire_score", 0) or 0

    all_players = data.get("players") or []
    if not all_players:
        return {"ok": False, "error": "В матче нет данных по игрокам"}

    # Находим целевого игрока
    target = None
    if target_account_id:
        try:
            aid = int(target_account_id)
            for p in all_players:
                if p.get("account_id") == aid:
                    target = p
                    break
        except Exception:
            pass

    if not target:
        # Если не передан или не найден — берем игрока с наибольшим импактом/GPM
        target = max(all_players, key=lambda p: (p.get("kills", 0) + p.get("assists", 0), p.get("gold_per_min", 0)))

    slot = target.get("player_slot", 0) or 0
    is_radiant = slot < 128
    is_win = (rad_win and is_radiant) or (not rad_win and not is_radiant)

    my_team = [p for p in all_players if (p.get("player_slot", 0) < 128) == is_radiant]
    enemy_team = [p for p in all_players if (p.get("player_slot", 0) < 128) != is_radiant]

    # Командные метрики
    team_kills = sum(p.get("kills", 0) or 0 for p in my_team) or 1
    team_damage = sum(p.get("hero_damage", 0) or 0 for p in my_team) or 1
    team_tower_dmg = sum(p.get("tower_damage", 0) or 0 for p in my_team) or 1

    # Личные метрики игрока
    k = target.get("kills", 0) or 0
    d = target.get("deaths", 0) or 0
    a = target.get("assists", 0) or 0
    kda_ratio = round((k + a) / max(1, d), 2)
    kp_pct = round(100.0 * (k + a) / team_kills, 1)

    h_dmg = target.get("hero_damage", 0) or 0
    t_dmg = target.get("tower_damage", 0) or 0
    dmg_share = round(100.0 * h_dmg / team_damage, 1)
    tower_share = round(100.0 * t_dmg / team_tower_dmg, 1)

    gpm = target.get("gold_per_min", 0) or 0
    xpm = target.get("xp_per_min", 0) or 0
    net_worth = target.get("total_gold", 0) or (gpm * dur_min)

    # Предметы
    items = []
    for i in range(6):
        iid = target.get("item_%d" % i)
        name = get_item_name(iid)
        if name:
            items.append(name)

    neutral = get_item_name(target.get("item_neutral"))

    hero_id = target.get("hero_id", 0)
    hero_name = HEROES_MAP.get(hero_id, "Hero_%d" % hero_id)

    # --- Алгоритмический вердикт и аудит ошибок ---
    strengths = []
    mistakes = []
    recommendations = []

    # 1. KDA и Смерти
    if d >= 10:
        mistakes.append("⚠️ Слишком много смертей (%d). Каждая смерть отдавала врагам темп и опыт." % d)
        recommendations.append("Держись ближе к вижну своей команды, не заходи соло во вражеский лес без информации по 3+ героям.")
    elif d <= 3 and dur_min >= 25:
        strengths.append("💎 Отличная выживаемость (всего %d смертей за %.1f мин)!" % (d, dur_min))

    if kda_ratio >= 4.0:
        strengths.append("🔥 Высокий боевой KDA коэффициент: %.2f" % kda_ratio)

    # 2. Участие в драках (Kill Participation)
    if kp_pct >= 65:
        strengths.append("⚔️ Огромное участие в командной игре: %0.1f%% от всех фрагов команды!" % kp_pct)
    elif kp_pct < 40 and dur_min >= 25:
        mistakes.append("⚠️ Низкое участие в драках: всего %0.1f%% от фрагов команды (много AFK-фарма или запоздалые ТП)." % kp_pct)
        recommendations.append("Всегда носи Town Portal Scroll и прилетай в драки под своими вышками.")

    # 3. Нанесение урона
    if dmg_share >= 30:
        strengths.append("💥 Ты нанёс %0.1f%% всего урона команды (топ DPS)." % dmg_share)
    elif dmg_share < 15 and "Carry" in (target.get("roles") or []):
        mistakes.append("⚠️ Низкий урон для кора: всего %0.1f%% от общего урона команды." % dmg_share)

    if tower_share >= 35:
        strengths.append("🏰 Высокий урон по строениям: %0.1f%% урона команды по вышкам!" % tower_share)

    # 4. Анализ артефактов против драфта врага
    enemy_names = [HEROES_MAP.get(p.get("hero_id", 0), "") for p in enemy_team]
    enemy_items = []
    for ep in enemy_team:
        for idx in range(6):
            ename = get_item_name(ep.get("item_%d" % idx))
            if ename:
                enemy_items.append(ename)

    # Проверка на Evasion (уклонения)
    has_evasion_enemy = any(h in ("Phantom Assassin", "Windranger", "Brewmaster") for h in enemy_names) or any("Butterfly" in it for it in enemy_items)
    has_true_strike = any(it in ("Monkey King Bar", "Bloodthorn") for it in items)
    if has_evasion_enemy and not has_true_strike and gpm >= 500:
        mistakes.append("⚠️ У врагов были уклонения (PA/Butterfly), но у тебя не было MKB или Bloodthorn.")
        recommendations.append("Купи Monkey King Bar при наличии у врагов бабочек или пассивки Фантомки.")

    # Проверка на Сайленс / Дизейбл
    has_silence_enemy = any(h in ("Silencer", "Night Stalker", "Death Prophet") for h in enemy_names) or any("Orchid" in it or "Bloodthorn" in it for it in enemy_items)
    has_dispel = any(it in ("Black King Bar", "Lotus Orb", "Manta Style", "Eul's Scepter of Divinity", "Wind Waker", "Guardian Greaves") for it in items)
    if has_silence_enemy and not has_dispel:
        mistakes.append("⚠️ У врага был сайленс/орчид, но у тебя не было предмета на развеивание (Manta / BKB / Lotus).")
        recommendations.append("Против безмолвия собирай Lotus Orb, Manta Style или BKB.")

    # Положительные сборки
    if has_dispel:
        strengths.append("🛡️ Грамотная покупка диспела/защиты (BKB / Lotus / Manta).")

    # Итоговый структурированный отчет
    report = {
        "ok": True,
        "match_id": mid,
        "duration_min": dur_min,
        "result": "ПОБЕДА" if is_win else "ПОРАЖЕНИЕ",
        "score": "%s : %s" % (rad_score, dire_score),
        "player": {
            "hero": hero_name,
            "kda": "%d/%d/%d" % (k, d, a),
            "kda_ratio": kda_ratio,
            "kp_pct": kp_pct,
            "gpm": gpm,
            "xpm": xpm,
            "hero_damage": h_dmg,
            "dmg_share_pct": dmg_share,
            "tower_damage": t_dmg,
            "tower_share_pct": tower_share,
            "items": items,
            "neutral_item": neutral,
        },
        "enemies": enemy_names,
        "verdict": {
            "strengths": strengths,
            "mistakes": mistakes,
            "recommendations": recommendations,
        },
    }
    return report


def fmt_postgame_report(rep):
    """Форматирует отчет о матче в читаемый текст."""
    if not rep.get("ok"):
        return "Ошибка: %s" % rep.get("error")

    p = rep["player"]
    v = rep["verdict"]

    lines = []
    lines.append("════════════════════════════════════════════════════════════")
    lines.append("📊 ПОСТ-МАТЧ АНАЛИЗАТОР (МАТЧ #%s)" % rep["match_id"])
    lines.append("════════════════════════════════════════════════════════════")
    lines.append("🏆 ИТОГ: %s | Время: %.1f мин | Счёт: %s" % (rep["result"], rep["duration_min"], rep["score"]))
    lines.append("🦸 Герой: %s" % p["hero"])
    lines.append("⚔️ KDA: %s (KDA Ratio: %.2f | Участие в фрагах: %.1f%%)" % (p["kda"], p["kda_ratio"], p["kp_pct"]))
    lines.append("💰 Фарм: %d GPM | %d XPM" % (p["gpm"], p["xpm"]))
    lines.append("💥 Урон по героям: %d (%0.1f%% от команды)" % (p["hero_damage"], p["dmg_share_pct"]))
    lines.append("🏰 Урон по зданиям: %d (%0.1f%% от команды)" % (p["tower_damage"], p["tower_share_pct"]))
    
    if p["items"]:
        lines.append("🎒 Закуп: %s" % ", ".join(p["items"]))
    if p["neutral_item"]:
        lines.append("🔮 Нейтралка: %s" % p["neutral_item"])

    lines.append("")
    if v["strengths"]:
        lines.append("✅ ЧТО БЫЛО СДЕЛАНО ОТЛИЧНО:")
        for s in v["strengths"]:
            lines.append("  • %s" % s)
        lines.append("")

    if v["mistakes"]:
        lines.append("⚠️ КЛЮЧЕВЫЕ ОШИБКИ И СЛАБЫЕ МЕСТА:")
        for m in v["mistakes"]:
            lines.append("  • %s" % m)
        lines.append("")

    if v["recommendations"]:
        lines.append("💡 СОВЕТЫ ДЛЯ СЛЕДУЮЩЕЙ ИГРЫ:")
        for r in v["recommendations"]:
            lines.append("  • %s" % r)
        lines.append("")

    lines.append("════════════════════════════════════════════════════════════")
    return "\n".join(lines)


if __name__ == "__main__":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

    args = sys.argv[1:]
    if not args:
        print("Использование: python postgame_analyzer.py <match_id> [account_id]")
        sys.exit(0)

    mid = args[0]
    aid = args[1] if len(args) > 1 else None
    rep = analyze_match(mid, aid)
    print(fmt_postgame_report(rep))
