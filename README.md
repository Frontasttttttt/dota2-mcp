dota2-mcp — легальный MCP-сервер для Dota 2 (анализ, а не бот)

Легальный помощник: GSI в реальном времени + OpenDota/STRATZ + тренер + запуск игры.
НЕ играет за тебя в матчмейкинге, НЕ управляет героем, НЕ перехватывает ввод. VAC-safe.

## Состав

- `server.py` — MCP-сервер (stdio, stdlib-only, без pip-зависимостей)
- `gsi_server.py` — HTTP-приёмник Game State Integration (http://127.0.0.1:3000)
- `coach_data.json` — советы тренера: тайминги, пик-советы, базовые билды
- `config.json` — твой account_id, пути Steam/Dota, порт GSI
- `tools/install_gsi.py` — установка GSI-конфига в Dota
- `README.md` — этот файл

## Быстрый старт (Windows, PowerShell)

```powershell
cd C:\AI\dota2-mcp

# 1. Установить GSI-конфиг в обе найденные копии Dota (D: и E:)
python tools\install_gsi.py

# 2. Запустить GSI-приёмник (оставь окно открытым во время игры)
python gsi_server.py
# проверка: http://127.0.0.1:3000/status

# 3. Указать свой Dota account_id (числовой, НЕ steam64)
# Узнать: https://www.opendota.com -> залогинься -> цифры в URL, либо https://steamid.io
python server.py --set-account 123456789

# 4. Подключить к Claude Desktop / любому MCP-клиенту:
# Claude Desktop -> Settings -> Developer -> Edit Config -> claude_desktop_config.json:
```

```json
{
  "mcpServers": {
    "dota2": {
      "command": "python",
      "args": ["C:\\AI\\dota2-mcp\\server.py"],
      "cwd": "C:\\AI\\dota2-mcp"
    }
  }
}
```

Перезапусти Claude Desktop. Появятся инструменты `dota_*`.

## Инструменты MCP

| Инструмент | Что делает |
|---|---|
| `dota_launch` | Запускает Dota 2 через Steam (`-applaunch 570`). `mode=training` + инструкция по созданию лобби с ботами |
| `dota_gsi_status` | Жив ли GSI-приёмник, когда был последний пакет от игры |
| `dota_gsi_latest` | Последнее состояние игры: герой, HP/MP, KDA, GPM/XPM, карта, время |
| `dota_gsi_install` | Переустановить GSI-конфиг в Dota |
| `dota_set_account` / `dota_whoami` | Сохранить/показать account_id для OpenDota |
| `dota_profile` | Профиль OpenDota: MMR-оценка, винрейт, топ-герои |
| `dota_recent_matches` | Последние N матчей с KDA, героем, результатом |
| `dota_match_details` | Разбор конкретного match_id |
| `dota_hero_stats` | Твоя статистика на герое: матчи, винрейт |
| `dota_coach_tip` | Совет тренера по текущей игре (GSI) или герою: тайминги, предметы |
| `dota_pick_advice` | Совет по пику против 1–5 вражеских героев |
| `dota_item_guide` | Базовый билд на героя (стартовые → мид → лейт) |
| `dota_stratz_match` | Матч через STRATZ GraphQL (нужен `STRATZ_TOKEN`) |

## Как включить GSI в Dota 2

`tools/install_gsi.py` кладёт файл сюда (в обе копии):

- `D:\SteamLibrary\steamapps\common\dota 2 beta\game\dota\cfg\gamestate_integration\gamestate_integration_dota2mcp.cfg`
- `E:\SteamLibrary\steamapps\common\dota 2 beta\game\dota\cfg\gamestate_integration\...`

Содержимое шлёт POST на `http://127.0.0.1:3000` каждые 0.5 c.
GSI работает только пока запущен `python gsi_server.py` и идёт матч (или смотреть реплей).
Если Dota обновится/переустановится — запусти установку ещё раз.

## Тренировочное лобби с ботами (легально)

1. Вызови `dota_launch` с `mode=training` (игра запустится).
2. В игре: Играть → Тренировка с ботами → Выбери сложность → Начать.
Это официальный режим Valve, бана нет.

## STRATZ (опционально)

1. Получи токен: https://stratz.com/api
2. `setx STRATZ_TOKEN "твой_токен"` → перезапусти терминал
3. Вызывай `dota_stratz_match` с `match_id`.

## Проверка без Claude

```powershell
# список инструментов:
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | python server.py --oneshot
```
