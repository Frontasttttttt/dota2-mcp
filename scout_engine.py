"""scout_engine.py — Движок разведки игроков, детекции смурфов/бустеров и анализа пула героев.
100% бесплатно: OpenDota API + локальный кэш на диске (0 токенов нейросетей).
"""
import concurrent.futures
import io
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error

BASE = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE, "cache")
PLAYERS_CACHE_DIR = os.path.join(CACHE_DIR, "players")
HEROES_FILE = os.path.join(BASE, "heroes_cache.json")

os.makedirs(PLAYERS_CACHE_DIR, exist_ok=True)

# Загрузка локальных имен героев
HEROES_MAP = {}
try:
    with open(HEROES_FILE, encoding="utf-8") as f:
        for h in json.load(f) or []:
            HEROES_MAP[int(h["id"])] = h.get("localized_name", str(h["id"]))
except Exception:
    pass

# Список сигнатурных героев бустеров и смурфов
CHEESE_SMURF_HEROES = {
    1: "Anti-Mage",
    10: "Morphling",
    11: "Shadow Fiend",
    17: "Storm Spirit",
    34: "Tinker",
    39: "Queen of Pain",
    46: "Templar Assassin",
    59: "Huskar",
    61: "Broodmother",
    74: "Invoker",
    80: "Lone Druid",
    82: "Meepo",
    92: "Visage",
    93: "Slark",
    106: "Ember Spirit",
    113: "Arc Warden",
}

RANK_MEDALS = {
    1: "Herald",
    2: "Guardian",
    3: "Crusader",
    4: "Archon",
    5: "Legend",
    6: "Ancient",
    7: "Divine",
    8: "Immortal",
}


def _http_get(url, timeout=10):
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


def format_rank_tier(tier):
    """Преобразует rank_tier (например 51) в читаемый ранг (например Legend 1)."""
    if not tier or tier == 0:
        return "Unranked"
    try:
        tier = int(tier)
        medal_id = tier // 10
        stars = tier % 10
        medal = RANK_MEDALS.get(medal_id, "Rank")
        if medal_id == 8:
            return "Immortal"
        return "%s %d" % (medal, stars)
    except Exception:
        return "Rank %s" % tier


def parse_player_identifiers(raw_text):
    """Извлекает числовые 32-битные account_id из любого текста:
    - Ссылок OpenDota / Dotabuff
    - Steam3 [U:1:1092348748]
    - SteamID64 (7656119...)
    - Обычных чисел
    """
    if isinstance(raw_text, (list, tuple)):
        raw_text = " ".join(str(x) for x in raw_text)
    
    text = str(raw_text or "")
    ids = set()

    # 1. URL OpenDota / Dotabuff
    for m in re.finditer(r"(?:opendota\.com|dotabuff\.com|stratz\.com)/players/(\d+)", text, re.I):
        ids.add(int(m.group(1)))

    # 2. Steam3: [U:1:1092348748]
    for m in re.finditer(r"\[U:1:(\d+)\]", text, re.I):
        ids.add(int(m.group(1)))

    # 3. SteamID64 (7656119...)
    for m in re.finditer(r"\b(7656119\d{10})\b", text):
        s64 = int(m.group(1))
        ids.add(s64 - 76561197960265728)

    # 4. Чистые 32-bit ID (от 6 до 10 цифр, но не начинающиеся на 7656119)
    for m in re.finditer(r"\b(\d{6,10})\b", text):
        val = int(m.group(1))
        if not str(val).startswith("7656119"):
            ids.add(val)

    return sorted(list(ids))


def scout_player(account_id):
    """Глубокая разведка одного игрока: профиль, винрейт, недавние герои, смурф-анализ."""
    try:
        aid = int(account_id)
    except Exception:
        return {"ok": False, "error": "Неверный account_id"}

    cache_file = os.path.join(PLAYERS_CACHE_DIR, "%d.json" % aid)
    # Кэш на 20 минут
    if os.path.exists(cache_file):
        try:
            if time.time() - os.path.getmtime(cache_file) < 1200:
                with open(cache_file, encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass

    # Параллельный запрос к OpenDota (профиль + последние матчи)
    p_info, p_err = _http_get("https://api.opendota.com/api/players/%d" % aid)
    recent, r_err = _http_get("https://api.opendota.com/api/players/%d/recentMatches" % aid)

    if not p_info and not recent:
        return {"ok": False, "account_id": aid, "error": "Профиль закрыт или не найден в OpenDota"}

    profile = (p_info or {}).get("profile") or {}
    name = profile.get("personaname") or ("Player_%d" % aid)
    avatar = profile.get("avatarfull") or profile.get("avatarmedium")
    rank_tier = (p_info or {}).get("rank_tier") or 0
    rank_name = format_rank_tier(rank_tier)
    leaderboard_rank = (p_info or {}).get("leaderboard_rank")

    # Анализ последних 20 матчей
    recent_matches = recent or []
    total_recent = len(recent_matches)
    wins_count = 0
    hero_stats = {}
    total_kills = 0
    total_deaths = 0
    total_assists = 0
    total_gpm = 0

    for m in recent_matches:
        hid = m.get("hero_id")
        slot = m.get("player_slot", 0) or 0
        is_rad = slot < 128
        won = bool(m.get("radiant_win") == is_rad)
        if won:
            wins_count += 1

        k = m.get("kills", 0) or 0
        d = m.get("deaths", 0) or 0
        a = m.get("assists", 0) or 0
        gpm = m.get("gold_per_min", 0) or 0

        total_kills += k
        total_deaths += d
        total_assists += a
        total_gpm += gpm

        if hid not in hero_stats:
            hero_stats[hid] = {
                "hero_id": hid,
                "name": HEROES_MAP.get(hid, "Hero_%d" % hid),
                "games": 0,
                "wins": 0,
                "kills": 0,
                "deaths": 0,
                "assists": 0,
                "gpm_sum": 0,
            }
        hero_stats[hid]["games"] += 1
        if won:
            hero_stats[hid]["wins"] += 1
        hero_stats[hid]["kills"] += k
        hero_stats[hid]["deaths"] += d
        hero_stats[hid]["assists"] += a
        hero_stats[hid]["gpm_sum"] += gpm

    winrate_pct = round(100.0 * wins_count / max(1, total_recent), 1) if total_recent > 0 else 50.0
    avg_kda = round((total_kills + total_assists) / max(1, total_deaths), 2) if total_recent > 0 else 2.0
    avg_gpm = round(total_gpm / max(1, total_recent)) if total_recent > 0 else 0

    # Сортируем топ героев последних каток
    top_heroes_raw = sorted(hero_stats.values(), key=lambda x: (x["games"], x["wins"]), reverse=True)
    recent_heroes = []
    for h in top_heroes_raw[:5]:
        h_wr = round(100.0 * h["wins"] / h["games"], 1)
        h_kda = round((h["kills"] + h["assists"]) / max(1, h["deaths"]), 2)
        recent_heroes.append({
            "hero_id": h["hero_id"],
            "hero_name": h["name"],
            "games": h["games"],
            "wins": h["wins"],
            "winrate_pct": h_wr,
            "avg_kda": h_kda,
            "avg_gpm": round(h["gpm_sum"] / max(1, h["games"])),
            "is_smurf_hero": h["hero_id"] in CHEESE_SMURF_HEROES,
        })

    # --- Детекция Смурфа / Бустера ---
    smurf_score = 0
    triggers = []

    # 1. Аномальный винрейт за последние матчи
    if total_recent >= 12:
        if winrate_pct >= 80.0:
            smurf_score += 45
            triggers.append("🔥 Сверхвысокий винрейт: %0.1f%% (%d из %d побед)!" % (winrate_pct, wins_count, total_recent))
        elif winrate_pct >= 70.0:
            smurf_score += 30
            triggers.append("⚡ Высокий винрейт в последних матчах: %0.1f%% (%d побед)." % (winrate_pct, wins_count))
        elif winrate_pct <= 35.0:
            triggers.append("❄️ Игрок на сильном лузстрике (винрейт %0.1f%%, тильт)." % winrate_pct)

    # 2. Боевой импакт и KDA
    if total_recent >= 8:
        if avg_kda >= 5.5:
            smurf_score += 30
            triggers.append("⚔️ Аномально высокий KDA: %.2f (в среднем убивает без смертей)." % avg_kda)
        elif avg_kda >= 4.2:
            smurf_score += 15
            triggers.append("🎯 Высокий средний KDA: %.2f." % avg_kda)

    # 3. Спам смурф/чиз-героев с безумным винрейтом
    cheese_spammed = []
    for h in recent_heroes:
        if h["is_smurf_hero"] and h["games"] >= 3 and h["winrate_pct"] >= 70.0:
            cheese_spammed.append("%s (%d игр, %0.0f%% WR)" % (h["hero_name"], h["games"], h["winrate_pct"]))

    if cheese_spammed:
        smurf_score += 35
        triggers.append("🚨 Опасный спамер буст-героев: %s!" % ", ".join(cheese_spammed))

    # Вычисляем статус
    if smurf_score >= 60:
        verdict_badge = "🚨 СМУРФ / БУСТЕР"
        verdict_class = "danger"
    elif smurf_score >= 35:
        verdict_badge = "⚠️ ВИНСТРИК / СИЛЬНЫЙ"
        verdict_class = "warning"
    elif winrate_pct <= 35.0 and total_recent >= 10:
        verdict_badge = "❄️ ЛУЗСТРИК / ТИЛЬТ"
        verdict_class = "tilt"
    else:
        verdict_badge = "🟢 ОБЫЧНЫЙ ИГРОК"
        verdict_class = "normal"

    # Тактический совет
    tips = []
    if cheese_spammed:
        first_cheese = recent_heroes[0]["hero_name"]
        tips.append("Рекомендуется забанить %s или взять контрпик с точечным дизейблом." % first_cheese)
    elif recent_heroes and recent_heroes[0]["winrate_pct"] >= 70.0 and recent_heroes[0]["games"] >= 3:
        tips.append("Забанить сигнатурку: %s (%0.0f%% WR)." % (recent_heroes[0]["hero_name"], recent_heroes[0]["winrate_pct"]))
    elif verdict_class == "tilt":
        tips.append("Игрок в тильте — активно гангайте его линию для деморализации.")

    result = {
        "ok": True,
        "account_id": aid,
        "name": name,
        "avatar": avatar,
        "rank_tier": rank_tier,
        "rank_name": rank_name,
        "leaderboard_rank": leaderboard_rank,
        "recent_summary": {
            "matches_analyzed": total_recent,
            "wins": wins_count,
            "losses": total_recent - wins_count,
            "winrate_pct": winrate_pct,
            "avg_kda": avg_kda,
            "avg_gpm": avg_gpm,
        },
        "recent_heroes": recent_heroes,
        "smurf_verdict": {
            "score": smurf_score,
            "badge": verdict_badge,
            "class": verdict_class,
            "is_smurf_threat": smurf_score >= 35,
            "triggers": triggers,
            "tips": tips,
        },
    }

    # Сохраняем в кэш
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False)
    except Exception:
        pass

    return result


def scout_lobby(identifiers_raw):
    """Разведка всего лобби (до 10 игроков параллельно)."""
    ids = parse_player_identifiers(identifiers_raw)
    if not ids:
        return {"ok": False, "error": "Не удалось найти ни одного account_id"}

    results = []
    # Параллельный опрос до 5 потоков (быстро и не перегружает сеть)
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_map = {executor.submit(scout_player, aid): aid for aid in ids[:10]}
        for future in concurrent.futures.as_completed(future_map):
            try:
                res = future.result()
                results.append(res)
            except Exception as e:
                aid = future_map[future]
                results.append({"ok": False, "account_id": aid, "error": str(e)})

    # Сортируем: сначала смурфы/бустеры по убыванию угрозы
    results.sort(
        key=lambda x: (
            x.get("smurf_verdict", {}).get("score", 0) if x.get("ok") else -1,
            x.get("recent_summary", {}).get("winrate_pct", 0) if x.get("ok") else -1,
        ),
        reverse=True,
    )

    return {"ok": True, "players_count": len(results), "players": results}


def fmt_player_scout(p):
    """Красивая короткая выписка по игроку для терминала и MCP."""
    if not p.get("ok"):
        return "❌ ID %s: %s" % (p.get("account_id"), p.get("error"))

    s = p["recent_summary"]
    v = p["smurf_verdict"]

    lines = []
    lines.append("👤 %s [%s] (ID: %s) — %s" % (p["name"], p["rank_name"], p["account_id"], v["badge"]))
    lines.append("   Форма: %dW - %dL (%0.1f%% WR) | KDA: %.2f | GPM: %d" % (
        s["wins"], s["losses"], s["winrate_pct"], s["avg_kda"], s["avg_gpm"]
    ))

    # Топ герои
    h_strs = []
    for h in p.get("recent_heroes", [])[:3]:
        h_strs.append("%s (%d игр, %0.0f%% WR)" % (h["hero_name"], h["games"], h["winrate_pct"]))
    if h_strs:
        lines.append("   Пул последних игр: " + ", ".join(h_strs))

    if v.get("triggers"):
        for t in v["triggers"]:
            lines.append("   %s" % t)

    if v.get("tips"):
        for tip in v["tips"]:
            lines.append("   💡 Совет: %s" % tip)

    return "\n".join(lines)


def fmt_lobby_report(lobby):
    """Отчет по всему лобби."""
    if not lobby.get("ok"):
        return "Ошибка: %s" % lobby.get("error")

    lines = []
    lines.append("══════════════════════════════════════════════════════════════════")
    lines.append("🕵️ РАЗВЕДКА ЛОББИ И СМУРФ-РАДАР (Игроков: %d)" % lobby["players_count"])
    lines.append("══════════════════════════════════════════════════════════════════")
    for i, p in enumerate(lobby.get("players", []), 1):
        lines.append("%d. %s" % (i, fmt_player_scout(p)))
        lines.append("──────────────────────────────────────────────────────────────────")
    return "\n".join(lines)


if __name__ == "__main__":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

    args = sys.argv[1:]
    if not args:
        print("Использование: python scout_engine.py <account_id... или ссылки/текст>")
        print("Пример: python scout_engine.py 1092348748")
        print("Пример: python scout_engine.py 1092348748 76561199052614476")
        sys.exit(0)

    res = scout_lobby(" ".join(args))
    print(fmt_lobby_report(res))
