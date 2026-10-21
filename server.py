"""MCP stdio-сервер: JSON-RPC по stdin/stdout. Stdlib-only."""
import io
import json
import sys
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass
import dota_tools_a as A
import dota_tools_b as B

TOOLS = [
    {"name": "dota_launch", "description": "Запустить Dota 2. mode=training - инструкция по лобби с ботами.",
     "inputSchema": {"type": "object", "properties": {"mode": {"type": "string"}, "hero": {"type": "string"}}}},
    {"name": "dota_gsi_status", "description": "Статус GSI-приёмника.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "dota_gsi_latest", "description": "Последнее состояние игры из GSI (герой, HP/MP, KDA, таймеры, золото).",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "dota_gsi_install", "description": "Установить GSI-конфиг в Dota 2.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "dota_set_account", "description": "Сохранить числовой Dota account_id.",
     "inputSchema": {"type": "object", "properties": {"account_id": {"type": "integer"}}, "required": ["account_id"]}},
    {"name": "dota_whoami", "description": "Показать текущий сохраненный account_id.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "dota_profile", "description": "Профиль OpenDota: винрейт, ранг, сигнатурные герои.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "dota_recent_matches", "description": "Последние матчи игрока.",
     "inputSchema": {"type": "object", "properties": {"limit": {"type": "integer"}}}},
    {"name": "dota_match_details", "description": "Глубокий пост-матч разбор: KDA, участие в драках, урон, аудит артефактов и ошибок.",
     "inputSchema": {"type": "object", "properties": {"match_id": {"type": "integer"}}, "required": ["match_id"]}},
    {"name": "dota_hero_stats", "description": "Статистика игрока на конкретном герое.",
     "inputSchema": {"type": "object", "properties": {"hero_id": {"type": "integer"}}, "required": ["hero_id"]}},
    {"name": "dota_coach_tip", "description": "Совет тренера по таймингам карты или стадии игры.",
     "inputSchema": {"type": "object", "properties": {"hero": {"type": "string"}, "minute": {"type": "integer"}}}},
    {"name": "dota_live_tick", "description": "Живой тик трекера: сейчас + темп/дельта за 1 и 5 мин (факт GPM/LH), вердикт.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "dota_spectate_live", "description": "Максимум инфы при просмотре друга: GSI spectator + OpenDota live + разбор.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "dota_pick_advice", "description": "Глубокий драфт-анализ и контрпики против 1-5 врагов (все 124+ героя, сленг, статистика OpenDota, аудит урона/контроля/пассивок, шмотки).",
     "inputSchema": {"type": "object", "properties": {"enemies": {"type": ["array", "string"], "items": {"type": "string"}}}}},
    {"name": "dota_item_guide", "description": "Билд на героя по стадиям игры.",
     "inputSchema": {"type": "object", "properties": {"hero": {"type": "string"}}, "required": ["hero"]}},
    {"name": "dota_stratz_match", "description": "Матч через STRATZ GraphQL (при наличии STRATZ_TOKEN).",
     "inputSchema": {"type": "object", "properties": {"match_id": {"type": "integer"}}, "required": ["match_id"]}},
]

DISPATCH = {
    "dota_launch": lambda a: A.t_launch(a.get("mode", "normal"), a.get("hero")),
    "dota_gsi_status": lambda a: A.t_gsi_status(),
    "dota_gsi_latest": lambda a: A.t_gsi_latest(),
    "dota_gsi_install": lambda a: A.t_gsi_install(),
    "dota_set_account": lambda a: A.t_set_account(a.get("account_id")),
    "dota_whoami": lambda a: {"ok": True, "account_id": __import__("dota_core").CFG.get("account_id")},
    "dota_profile": lambda a: A.t_profile(),
    "dota_recent_matches": lambda a: B.t_recent_matches(a.get("limit", 10)),
    "dota_match_details": lambda a: B.t_match_details(a.get("match_id")),
    "dota_hero_stats": lambda a: B.t_hero_stats(a.get("hero_id")),
    "dota_coach_tip": lambda a: B.t_coach_tip(a.get("hero"), a.get("minute")),
    "dota_live_tick": lambda a: B.t_live_tick(),
    "dota_spectate_live": lambda a: B.t_spectate_live(),
    "dota_pick_advice": lambda a: B.t_pick_advice(a.get("enemies", [])),
    "dota_item_guide": lambda a: B.t_item_guide(a.get("hero", "")),
    "dota_stratz_match": lambda a: B.t_stratz_match(a.get("match_id")),
}


def handle(msg):
    mid = msg.get("id")
    method = msg.get("method")
    params = msg.get("params") or {}

    def ok(result):
        return {"jsonrpc": "2.0", "id": mid, "result": result}

    def err(code, message):
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}

    if method == "initialize":
        return ok({"protocolVersion": "2024-11-05", "capabilities": {"tools": {}},
                   "serverInfo": {"name": "dota2-mcp", "version": "1.1.0"}})
    if method in ("notifications/initialized", "notifications/cancelled"):
        return None
    if method == "tools/list":
        return ok({"tools": TOOLS})
    if method == "tools/call":
        fn = DISPATCH.get(params.get("name"))
        if not fn:
            return err(-32602, "нет инструмента: %s" % params.get("name"))
        try:
            out = fn(params.get("arguments") or {})
        except Exception as e:
            out = {"ok": False, "error": str(e)}
        return ok({"content": [{"type": "text", "text": json.dumps(out, ensure_ascii=False, indent=2)}]})
    if method == "ping":
        return ok({})
    return err(-32601, "метод: %s" % method)


def main():
    while True:
        try:
            line = sys.stdin.readline()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except Exception:
            continue
        resp = handle(msg)
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
