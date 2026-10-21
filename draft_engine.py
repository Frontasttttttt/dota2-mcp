"""draft_engine.py — Движок анализа драфта и контрпиков для Dota 2.
100% бесплатно: OpenDota API + локальный кэш на диске + чистая математика.
Понимает народный сленг, аббревиатуры и русские названия.
"""
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
MATCHUPS_DIR = os.path.join(CACHE_DIR, "matchups")
HEROES_FILE = os.path.join(BASE, "heroes_cache.json")
HERO_STATS_FILE = os.path.join(CACHE_DIR, "hero_stats.json")

os.makedirs(MATCHUPS_DIR, exist_ok=True)

# ----------------- Словарь народного сленга и никнеймов -----------------
ALIASES = {
    # Сокращения и сленг
    "am": "Anti-Mage", "антимаг": "Anti-Mage", "магина": "Anti-Mage",
    "axe": "Axe", "акс": "Axe",
    "bane": "Bane", "бейн": "Bane", "атропос": "Bane",
    "bs": "Bloodseeker", "сикер": "Bloodseeker", "бс": "Bloodseeker", "бладсикер": "Bloodseeker",
    "cm": "Crystal Maiden", "цм": "Crystal Maiden", "цмка": "Crystal Maiden", "кристалка": "Crystal Maiden",
    "drow": "Drow Ranger", "тракса": "Drow Ranger", "тракс": "Drow Ranger", "дровка": "Drow Ranger",
    "es": "Earthshaker", "шейкер": "Earthshaker", "землетряс": "Earthshaker",
    "jugg": "Juggernaut", "джаггер": "Juggernaut", "джаг": "Juggernaut", "юнгер": "Juggernaut",
    "potm": "Mirana", "мирана": "Mirana", "потва": "Mirana",
    "morph": "Morphling", "морф": "Morphling", "морфлинг": "Morphling",
    "sf": "Shadow Fiend", "сф": "Shadow Fiend", "невермор": "Shadow Fiend", "койлер": "Shadow Fiend",
    "pl": "Phantom Lancer", "пл": "Phantom Lancer", "лансер": "Phantom Lancer",
    "puck": "Puck", "пак": "Puck",
    "pudge": "Pudge", "пудж": "Pudge", "падж": "Pudge", "бучер": "Pudge", "мясник": "Pudge",
    "razor": "Razor", "разор": "Razor", "рейзор": "Razor", "электрик": "Razor",
    "sk": "Sand King", "ск": "Sand King", "скорпион": "Sand King", "скорп": "Sand King",
    "storm": "Storm Spirit", "шторм": "Storm Spirit", "панда": "Storm Spirit",
    "sven": "Sven", "свен": "Sven",
    "tiny": "Tiny", "тини": "Tiny", "тинька": "Tiny", "камень": "Tiny",
    "vs": "Vengeful Spirit", "венга": "Vengeful Spirit",
    "wr": "Windranger", "вр": "Windranger", "виндра": "Windranger", "рыжая": "Windranger",
    "zeus": "Zeus", "зевс": "Zeus", "дедушка": "Zeus",
    "kunkka": "Kunkka", "кунка": "Kunkka", "адмирал": "Kunkka", "капитан": "Kunkka",
    "lina": "Lina", "лина": "Lina",
    "lion": "Lion", "лион": "Lion", "леон": "Lion",
    "rhasta": "Shadow Shaman", "шаман": "Shadow Shaman", "расту": "Shadow Shaman", "расто": "Shadow Shaman",
    "slardar": "Slardar", "селедка": "Slardar", "селёдка": "Slardar", "слардар": "Slardar",
    "tide": "Tidehunter", "тайд": "Tidehunter", "арбуз": "Tidehunter",
    "wd": "Witch Doctor", "вд": "Witch Doctor", "доктор": "Witch Doctor",
    "lich": "Lich", "лич": "Lich",
    "riki": "Riki", "рики": "Riki", "крыса": "Riki",
    "enigma": "Enigma", "энигма": "Enigma",
    "tinker": "Tinker", "тинкер": "Tinker", "бош": "Tinker",
    "sniper": "Sniper", "снайпер": "Sniper", "дед": "Sniper", "кардан": "Sniper",
    "necro": "Necrophos", "некр": "Necrophos", "некрофос": "Necrophos",
    "warlock": "Warlock", "варлок": "Warlock", "голем": "Warlock",
    "bm": "Beastmaster", "бист": "Beastmaster", "бистмастер": "Beastmaster",
    "qop": "Queen of Pain", "квопа": "Queen of Pain", "акаша": "Queen of Pain",
    "veno": "Venomancer", "веник": "Venomancer", "веномансер": "Venomancer", "сопля": "Venomancer",
    "fv": "Faceless Void", "войд": "Faceless Void", "купол": "Faceless Void",
    "wk": "Wraith King", "вк": "Wraith King", "леорик": "Wraith King", "папич": "Wraith King", "скелет": "Wraith King",
    "dp": "Death Prophet", "баньша": "Death Prophet", "дп": "Death Prophet",
    "pa": "Phantom Assassin", "па": "Phantom Assassin", "мортра": "Phantom Assassin", "мортред": "Phantom Assassin", "фантомка": "Phantom Assassin",
    "pugna": "Pugna", "пугна": "Pugna",
    "ta": "Templar Assassin", "та": "Templar Assassin", "ланая": "Templar Assassin", "темпларка": "Templar Assassin",
    "viper": "Viper", "вайпер": "Viper",
    "luna": "Luna", "луна": "Luna",
    "dk": "Dragon Knight", "дк": "Dragon Knight", "дракон": "Dragon Knight", "давион": "Dragon Knight",
    "dazzle": "Dazzle", "даззл": "Dazzle", "дазл": "Dazzle",
    "clock": "Clockwerk", "клок": "Clockwerk", "клокверк": "Clockwerk", "бочка": "Clockwerk",
    "leshrac": "Leshrac", "леший": "Leshrac", "лешрак": "Leshrac", "дискотека": "Leshrac",
    "np": "Nature's Prophet", "фурион": "Nature's Prophet", "пень": "Nature's Prophet", "профет": "Nature's Prophet",
    "naix": "Lifestealer", "гуля": "Lifestealer", "найкс": "Lifestealer", "наикс": "Lifestealer",
    "ds": "Dark Seer", "дс": "Dark Seer", "дарксир": "Dark Seer",
    "clinkz": "Clinkz", "клинкз": "Clinkz", "боник": "Clinkz",
    "omni": "Omniknight", "омник": "Omniknight",
    "enchantress": "Enchantress", "энча": "Enchantress", "коза": "Enchantress", "олениха": "Enchantress",
    "huskar": "Huskar", "хускар": "Huskar", "хуск": "Huskar",
    "ns": "Night Stalker", "баланар": "Night Stalker", "нс": "Night Stalker",
    "brood": "Broodmother", "бруда": "Broodmother", "паучиха": "Broodmother", "паук": "Broodmother",
    "bh": "Bounty Hunter", "бх": "Bounty Hunter", "баунти": "Bounty Hunter", "гондор": "Bounty Hunter",
    "weaver": "Weaver", "вивер": "Weaver", "жук": "Weaver",
    "jakiro": "Jakiro", "джакиро": "Jakiro", "двухголовый": "Jakiro",
    "bat": "Batrider", "бэт": "Batrider", "батрайдер": "Batrider",
    "chen": "Chen", "чен": "Chen",
    "spec": "Spectre", "спектра": "Spectre", "меркуриал": "Spectre",
    "aa": "Ancient Apparition", "аа": "Ancient Apparition", "аппарат": "Ancient Apparition", "сосулька": "Ancient Apparition",
    "doom": "Doom", "дум": "Doom", "люцифер": "Doom",
    "ursa": "Ursa", "урса": "Ursa", "медведь": "Ursa",
    "sb": "Spirit Breaker", "бара": "Spirit Breaker", "разгон": "Spirit Breaker",
    "gyro": "Gyrocopter", "гиро": "Gyrocopter", "вертолет": "Gyrocopter",
    "alch": "Alchemist", "алхимик": "Alchemist", "алхим": "Alchemist",
    "invo": "Invoker", "инвокер": "Invoker", "вокер": "Invoker", "карл": "Invoker",
    "silencer": "Silencer", "сало": "Silencer", "сайленсер": "Silencer",
    "od": "Outworld Destroyer", "од": "Outworld Destroyer", "дестр": "Outworld Destroyer", "деструктор": "Outworld Destroyer",
    "lycan": "Lycan", "ликан": "Lycan", "волк": "Lycan",
    "brew": "Brewmaster", "панда": "Brewmaster", "брю": "Brewmaster", "пивовар": "Brewmaster",
    "sd": "Shadow Demon", "шд": "Shadow Demon",
    "ld": "Lone Druid", "друид": "Lone Druid", "медведь": "Lone Druid", "силлабир": "Lone Druid",
    "ck": "Chaos Knight", "цк": "Chaos Knight", "рыцарь хаоса": "Chaos Knight", "конник": "Chaos Knight",
    "meepo": "Meepo", "мипо": "Meepo", "геомансер": "Meepo",
    "treant": "Treant Protector", "дерево": "Treant Protector", "трент": "Treant Protector",
    "ogre": "Ogre Magi", "огр": "Ogre Magi", "огрмаг": "Ogre Magi",
    "undying": "Undying", "зомби": "Undying", "андаинг": "Undying", "дирга": "Undying",
    "rubick": "Rubick", "рубик": "Rubick", "вор": "Rubick",
    "disruptor": "Disruptor", "дизраптор": "Disruptor", "тралл": "Disruptor",
    "nyx": "Nyx Assassin", "никс": "Nyx Assassin", "жук-убийца": "Nyx Assassin",
    "naga": "Naga Siren", "нага": "Naga Siren", "сирена": "Naga Siren",
    "kotl": "Keeper of the Light", "котл": "Keeper of the Light", "дед со светом": "Keeper of the Light", "эзалор": "Keeper of the Light",
    "io": "Io", "висп": "Io", "шарик": "Io", "wisp": "Io",
    "visage": "Visage", "визаж": "Visage", "птицы": "Visage",
    "slark": "Slark", "сларк": "Slark", "рыба": "Slark",
    "medusa": "Medusa", "медуза": "Medusa", "дуза": "Medusa",
    "troll": "Troll Warlord", "тролль": "Troll Warlord", "джахакал": "Troll Warlord",
    "centaur": "Centaur Warrunner", "кентавр": "Centaur Warrunner", "кент": "Centaur Warrunner",
    "magnus": "Magnus", "магнус": "Magnus", "магнорог": "Magnus",
    "timber": "Timbersaw", "тимбер": "Timbersaw", "пила": "Timbersaw",
    "bb": "Bristleback", "брист": "Bristleback", "бристл": "Bristleback", "ёж": "Bristleback", "еж": "Bristleback", "свин": "Bristleback",
    "tusk": "Tusk", "туск": "Tusk", "морж": "Tusk",
    "sky": "Skywrath Mage", "скаймаг": "Skywrath Mage", "петух": "Skywrath Mage",
    "abaddon": "Abaddon", "абаддон": "Abaddon", "абадон": "Abaddon",
    "et": "Elder Titan", "титан": "Elder Titan", "элдер титан": "Elder Titan",
    "lc": "Legion Commander", "легионка": "Legion Commander", "лк": "Legion Commander", "дуэлистка": "Legion Commander",
    "techies": "Techies", "течис": "Techies", "минер": "Techies", "минёр": "Techies",
    "ember": "Ember Spirit", "эмбер": "Ember Spirit",
    "earth": "Earth Spirit", "земеля": "Earth Spirit",
    "underlord": "Underlord", "питлорд": "Underlord", "андерлорд": "Underlord",
    "tb": "Terrorblade", "тб": "Terrorblade", "террор": "Terrorblade",
    "phoenix": "Phoenix", "феникс": "Phoenix", "птица": "Phoenix", "яйцо": "Phoenix",
    "oracle": "Oracle", "оракул": "Oracle",
    "ww": "Winter Wyvern", "виверна": "Winter Wyvern",
    "arc": "Arc Warden", "арк": "Arc Warden", "варден": "Arc Warden",
    "mk": "Monkey King", "мк": "Monkey King", "макака": "Monkey King", "обезьяна": "Monkey King",
    "dw": "Dark Willow", "ива": "Dark Willow", "фея": "Dark Willow",
    "pango": "Pangolier", "панго": "Pangolier", "пангольер": "Pangolier", "броненосец": "Pangolier",
    "grim": "Grimstroke", "грим": "Grimstroke", "гримстроук": "Grimstroke", "художник": "Grimstroke",
    "hoodwink": "Hoodwink", "белка": "Hoodwink", "худвинк": "Hoodwink",
    "void spirit": "Void Spirit", "войдспирит": "Void Spirit",
    "snapfire": "Snapfire", "бабка": "Snapfire", "снэп": "Snapfire", "снэпфайр": "Snapfire",
    "mars": "Mars", "марс": "Mars",
    "ringmaster": "Ringmaster", "рингмастер": "Ringmaster", "циркач": "Ringmaster",
    "dawnbreaker": "Dawnbreaker", "валькирия": "Dawnbreaker", "дб": "Dawnbreaker", "донбрейкер": "Dawnbreaker",
    "marci": "Marci", "марси": "Marci", "немая": "Marci",
    "pb": "Primal Beast", "праймал": "Primal Beast", "бист": "Primal Beast", "пб": "Primal Beast", "динозавр": "Primal Beast",
    "muerta": "Muerta", "муэрта": "Muerta",
    "kez": "Kez", "кез": "Kez", "птица-мечник": "Kez",
}


def _http_get(url, timeout=12):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
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


# ----------------- База героев -----------------
def load_heroes():
    try:
        with open(HEROES_FILE, encoding="utf-8") as f:
            return json.load(f) or []
    except Exception:
        return []


HEROES = load_heroes()
HEROES_BY_ID = {h["id"]: h for h in HEROES}
HEROES_BY_NAME = {h["localized_name"].lower(): h for h in HEROES}


def load_hero_stats():
    """Загрузить расширенную статистику (винрейты по рангам) с диска или OpenDota."""
    if os.path.exists(HERO_STATS_FILE):
        try:
            with open(HERO_STATS_FILE, encoding="utf-8") as f:
                data = json.load(f)
                if data and time.time() - os.path.getmtime(HERO_STATS_FILE) < 86400 * 3:  # 3 дня
                    return {h["id"]: h for h in data}
        except Exception:
            pass

    # Качаем свежую
    data, err = _http_get("https://api.opendota.com/api/heroStats")
    if data:
        try:
            with open(HERO_STATS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            return {h["id"]: h for h in data}
        except Exception:
            pass
    return {}


HERO_STATS = load_hero_stats()


def get_base_winrate(hero_id):
    """Базовый средний винрейт героя в паблике (по умолчанию 50.0)."""
    s = HERO_STATS.get(hero_id)
    if s:
        picks = s.get("pub_pick", 0) or 0
        wins = s.get("pub_win", 0) or 0
        if picks > 0:
            return round(100.0 * wins / picks, 2)
    return 50.0


# ----------------- Поиск и распознавание героев -----------------
def normalize_name(s):
    return re.sub(r"[\s\-_']+", "", str(s or "").lower())


def resolve_hero(query):
    """Находит героя по ID, имени, сленгу или опечатке."""
    if not query:
        return None

    # 1. По числу ID
    try:
        qid = int(query)
        if qid in HEROES_BY_ID:
            return HEROES_BY_ID[qid]
    except Exception:
        pass

    q_raw = str(query).strip().lower()
    q_norm = normalize_name(q_raw)

    # 2. Прямой поиск в сленге
    if q_raw in ALIASES:
        target = ALIASES[q_raw].lower()
        if target in HEROES_BY_NAME:
            return HEROES_BY_NAME[target]

    # 3. Точное совпадение с localized_name или name (npc_dota_hero_...)
    for h in HEROES:
        if normalize_name(h["localized_name"]) == q_norm:
            return h
        if normalize_name(h.get("name", "")) == q_norm:
            return h
        if h.get("name", "").replace("npc_dota_hero_", "") == q_raw:
            return h

    # 4. Префиксное совпадение в ALIASES
    for alias, full in ALIASES.items():
        if alias.startswith(q_raw) and len(q_raw) >= 2:
            target = full.lower()
            if target in HEROES_BY_NAME:
                return HEROES_BY_NAME[target]

    # 5. Подстрока в имени героя
    for h in HEROES:
        if q_norm in normalize_name(h["localized_name"]):
            return h

    return None


# ----------------- Загрузка и кэширование матчапов -----------------
def get_matchups(hero_id):
    """Возвращает список матчапов против hero_id (из кэша или OpenDota)."""
    cache_path = os.path.join(MATCHUPS_DIR, "%d.json" % hero_id)
    if os.path.exists(cache_path):
        try:
            # Кэш валиден 5 дней
            if time.time() - os.path.getmtime(cache_path) < 86400 * 5:
                with open(cache_path, encoding="utf-8") as f:
                    return json.load(f), None
        except Exception:
            pass

    # Качаем из OpenDota
    url = "https://api.opendota.com/api/heroes/%d/matchups" % hero_id
    data, err = _http_get(url)
    if err:
        # Если есть старый кэш — вернем его
        if os.path.exists(cache_path):
            try:
                with open(cache_path, encoding="utf-8") as f:
                    return json.load(f), None
            except Exception:
                pass
        return None, err

    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass

    return data, None


# ----------------- Главный аналитический модуль драфта -----------------
def analyze_enemies_draft(enemy_heroes):
    """Анализирует слабости, урон и механики выбранного пика врагов."""
    breakdown = {
        "physical_threat": 0,
        "magical_threat": 0,
        "stuns_count": 0,
        "has_invis": False,
        "has_illusions": False,
        "has_passives": False,
        "has_heavy_regen": False,
        "warnings": [],
        "item_counters": set(),
    }

    invis_heroes = {"Riki", "Clinkz", "Bounty Hunter", "Nyx Assassin", "Weaver", "Treant Protector", "Invoker"}
    illusion_heroes = {"Phantom Lancer", "Naga Siren", "Chaos Knight", "Terrorblade", "Meepo"}
    passive_heroes = {"Bristleback", "Phantom Assassin", "Spectre", "Huskar", "Viper", "Dragon Knight", "Tidehunter"}
    regen_heroes = {"Huskar", "Morphling", "Alchemist", "Necrophos", "Timbersaw", "Slark", "Abaddon"}

    for h in enemy_heroes:
        name = h["localized_name"]
        roles = h.get("roles", [])
        attr = h.get("primary_attr", "")

        # Урон
        if "Nuker" in roles or attr == "int":
            breakdown["magical_threat"] += 1
        if "Carry" in roles or attr == "agi":
            breakdown["physical_threat"] += 1

        # Контроль
        if "Disabler" in roles:
            breakdown["stuns_count"] += 1

        # Механики
        if name in invis_heroes:
            breakdown["has_invis"] = True
            breakdown["item_counters"].add("Dust of Appearance / Sentry Wards")
            breakdown["item_counters"].add("Gem of True Sight (мид/лейт)")

        if name in illusion_heroes:
            breakdown["has_illusions"] = True
            breakdown["item_counters"].add("Maelstrom / Mjollnir (против иллюзий)")
            breakdown["item_counters"].add("Shiva's Guard")

        if name in passive_heroes:
            breakdown["has_passives"] = True
            breakdown["item_counters"].add("Silver Edge (Break пассивок)")

        if name in regen_heroes:
            breakdown["has_heavy_regen"] = True
            breakdown["item_counters"].add("Spirit Vessel / Shiva / Eye of Skadi (срез хила)")

        if name in ("Phantom Assassin", "Windranger", "Brewmaster", "Tinker"):
            breakdown["item_counters"].add("Monkey King Bar / Bloodthorn (True Strike против уклонений)")

    # Стратегические выводы
    n = len(enemy_heroes)
    if breakdown["stuns_count"] <= 1 and n >= 2:
        breakdown["warnings"].append(
            "⚠️ У врага ОЧЕНЬ мало надёжного контроля (станов)! Мобильные герои (Slark, Weaver, Storm Spirit, Tinker, Morphling, Anti-Mage) получат полную свободу."
        )
    elif breakdown["stuns_count"] >= 3:
        breakdown["warnings"].append(
            "🛡️ У врага плотный контроль (3+ дизейблера). В драфте обязательны BKB, Lotus Orb или Linken's Sphere, герои с встроенным диспелом (Slark, Abaddon, Legion Commander)."
        )

    if breakdown["magical_threat"] >= 3 and breakdown["physical_threat"] <= 1:
        breakdown["warnings"].append(
            "⚡ Огромный перевес в магический прокаст! Ранний Pipe of Insight, Mage Slayer и Glimmer Cape полностью сломают игру врагу."
        )
    elif breakdown["physical_threat"] >= 3 and breakdown["magical_threat"] <= 1:
        breakdown["warnings"].append(
            "⚔️ Враг бьёт почти исключительно физическим уроном! Покупайте Crimson Guard, Ghost Scepter, Shiva's Guard и пикайте героев с высокой бронёй."
        )

    return breakdown


def get_draft_advice(enemies_input):
    """Главная функция: получает список врагов (строки или числа)
    и выдает математический расчет топ-контрпиков и стратегию.
    """
    if isinstance(enemies_input, str):
        # Разделяем по запятым, пробелам, переносам строк
        tokens = [t.strip() for t in re.split(r"[,;\n\s]+", enemies_input) if t.strip()]
    elif isinstance(enemies_input, (list, tuple)):
        tokens = [str(x).strip() for x in enemies_input if str(x).strip()]
    else:
        tokens = []

    if not tokens:
        return {"ok": False, "error": "Укажи хотя бы одного героя врага (напр: pick sniper riki или pick od am)"}

    # Резолвим врагов
    enemies = []
    not_found = []
    enemy_ids = set()

    for tok in tokens:
        h = resolve_hero(tok)
        if h:
            if h["id"] not in enemy_ids:
                enemies.append(h)
                enemy_ids.add(h["id"])
        else:
            not_found.append(tok)

    if not enemies:
        return {
            "ok": False,
            "error": "Не удалось распознать героев: %s. Попробуй сленг (сф, ам, па, пудж) или англ. имя." % ", ".join(not_found),
        }

    # Для каждого врага собираем матчапы
    # candidate_scores: { hero_id: { "adv_sum": float, "wr_sum": float, "count": int, "details": [] } }
    candidate_scores = {}

    for e in enemies:
        eid = e["id"]
        matchups, err = get_matchups(eid)
        if not matchups:
            continue

        for m in matchups:
            cid = m.get("hero_id")
            if cid in enemy_ids or cid not in HEROES_BY_ID:
                continue

            gp = m.get("games_played", 0)
            w = m.get("wins", 0)
            if gp < 15:  # Мало матчей для достоверности
                continue

            wr = round(100.0 * w / gp, 2)
            base_wr = get_base_winrate(cid)
            adv = round(wr - base_wr, 2)  # Преимущество над базовым винрейтом

            if cid not in candidate_scores:
                candidate_scores[cid] = {"adv_sum": 0.0, "wr_sum": 0.0, "count": 0, "vs": {}}

            candidate_scores[cid]["adv_sum"] += adv
            candidate_scores[cid]["wr_sum"] += wr
            candidate_scores[cid]["count"] += 1
            candidate_scores[cid]["vs"][e["localized_name"]] = {"winrate": wr, "adv": adv, "games": gp}

    # Фильтруем кандидатов, у которых есть данные по ВСЕМ запрошенным врагам (или большинству)
    ranked = []
    num_e = len(enemies)

    for cid, s in candidate_scores.items():
        if s["count"] < num_e:
            continue
        h = HEROES_BY_ID[cid]
        avg_adv = round(s["adv_sum"] / num_e, 2)
        avg_wr = round(s["wr_sum"] / num_e, 2)

        # Классификация роли
        roles = h.get("roles", [])
        is_carry = "Carry" in roles
        is_support = "Support" in roles

        role_tag = "Support" if (is_support and not is_carry) else ("Carry / Core" if is_carry else "Offlane / Mid")

        ranked.append({
            "hero_id": cid,
            "name": h["localized_name"],
            "role": role_tag,
            "roles_full": roles,
            "advantage": avg_adv,
            "avg_winrate": avg_wr,
            "details": s["vs"],
        })

    # Сортируем по среднему преимуществу
    ranked.sort(key=lambda x: (x["advantage"], x["avg_winrate"]), reverse=True)

    # Разделяем на Core и Support
    top_overall = ranked[:7]
    top_cores = [c for c in ranked if "Core" in c["role"] or "Carry" in c["role"]][:4]
    top_supports = [c for c in ranked if "Support" in c["role"]][:4]

    # Анализ драфта
    analysis = analyze_enemies_draft(enemies)

    result = {
        "ok": True,
        "enemies": [e["localized_name"] for e in enemies],
        "not_found": not_found if not_found else None,
        "analysis": {
            "warnings": analysis["warnings"],
            "recommended_items": sorted(list(analysis["item_counters"])),
            "stuns_count": analysis["stuns_count"],
        },
        "top_counters": [
            {
                "hero": c["name"],
                "role": c["role"],
                "advantage": ("%+0.2f%%" % c["advantage"]),
                "winrate": ("%0.1f%%" % c["avg_winrate"]),
            }
            for c in top_overall
        ],
        "top_cores": [
            {
                "hero": c["name"],
                "advantage": ("%+0.2f%%" % c["advantage"]),
                "winrate": ("%0.1f%%" % c["avg_winrate"]),
            }
            for c in top_cores
        ],
        "top_supports": [
            {
                "hero": c["name"],
                "advantage": ("%+0.2f%%" % c["advantage"]),
                "winrate": ("%0.1f%%" % c["avg_winrate"]),
            }
            for c in top_supports
        ],
    }

    return result


def fmt_draft_advice(res):
    """Форматирует результат в читаемый текст для CLI и MCP."""
    if not res.get("ok"):
        return "Ошибка: %s" % res.get("error")

    lines = []
    lines.append("🎯 РАЗБОР ДРАФТА ПРОТИВ: %s" % ", ".join(res["enemies"]))
    if res.get("not_found"):
        lines.append("⚠️ Не распознаны: %s" % ", ".join(res["not_found"]))

    lines.append("")
    an = res.get("analysis", {})
    if an.get("warnings"):
        lines.append("⚡ АНАЛИЗ УЯЗВИМОСТЕЙ ВРАГА:")
        for w in an["warnings"]:
            lines.append("  %s" % w)
        lines.append("")

    if an.get("recommended_items"):
        lines.append("🎒 КЛЮЧЕВЫЕ АРТЕФАКТЫ ПРОТИВ ЭТОГО ПИКА:")
        for it in an["recommended_items"]:
            lines.append("  • %s" % it)
        lines.append("")

    lines.append("👑 ТОП-7 КОНТРПИКОВ (ПО ПРЕИМУЩЕСТВУ В ПАТЧЕ):")
    for i, c in enumerate(res.get("top_counters", []), 1):
        lines.append("  %d. %-20s [%-14s] Преимущество: %s (Винрейт: %s)" % (
            i, c["hero"], c["role"], c["advantage"], c["winrate"]
        ))

    lines.append("")
    if res.get("top_cores"):
        lines.append("⚔️ Лучшие коры (Carry / Mid):")
        for c in res["top_cores"]:
            lines.append("  • %-18s %s (WR %s)" % (c["hero"], c["advantage"], c["winrate"]))

    if res.get("top_supports"):
        lines.append("🛡️ Лучшие саппорты:")
        for c in res["top_supports"]:
            lines.append("  • %-18s %s (WR %s)" % (c["hero"], c["advantage"], c["winrate"]))

    return "\n".join(lines)


if __name__ == "__main__":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

    args = sys.argv[1:]
    if not args:
        print("Использование: python draft_engine.py <враги...>")
        print("Пример: python draft_engine.py sniper riki")
        print("Пример: python draft_engine.py сф од пудж")
        sys.exit(0)

    out = get_draft_advice(" ".join(args))
    print(fmt_draft_advice(out))
