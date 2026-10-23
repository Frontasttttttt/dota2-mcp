"""Установка GSI-конфига в найденные копии Dota 2."""
import io
import json
import os
import sys

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

GSI_CFG = '''"Dota2MCP"
{
  "uri"               "http://127.0.0.1:3000"
  "timeout"           "5.0"
  "buffer"            "0.0"
  "throttle"          "0.1"
  "heartbeat"         "5.0"
  "auth"
  {
    "token"           "dota2mcp"
  }
  "data"
  {
    "provider"        "1"
    "map"             "1"
    "player"          "1"
    "allplayers"      "1"
    "hero"            "1"
    "abilities"       "1"
    "items"           "1"
    "buildings"       "1"
    "events"          "1"
    "draft"           "1"
    "wearables"       "1"
    "league"          "1"
  }
}
'''

DEFAULT_INSTALLS = [
    r"D:\SteamLibrary\steamapps\common\dota 2 beta",
    r"E:\SteamLibrary\steamapps\common\dota 2 beta",
]


def install_to(dota_root, port=3000):
    cfg_dir = os.path.join(dota_root, "game", "dota", "cfg", "gamestate_integration")
    os.makedirs(cfg_dir, exist_ok=True)
    text = GSI_CFG.replace("127.0.0.1:3000", "127.0.0.1:%d" % port)
    path = os.path.join(cfg_dir, "gamestate_integration_dota2mcp.cfg")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def main():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg_path = os.path.join(base, "config.json")
    port = 3000
    roots = DEFAULT_INSTALLS
    try:
        with open(cfg_path, encoding="utf-8") as f:
            c = json.load(f)
            port = int(c.get("gsi_port", 3000))
            roots = c.get("dota_installs") or roots
    except Exception:
        pass

    found = False
    for r in roots:
        if os.path.exists(r):
            p = install_to(r, port)
            print("Установлен GSI-конфиг:", p)
            found = True
        else:
            print("Папка не найдена:", r)
    if not found:
        print("ВНИМАНИЕ: Dota 2 не найдена по стандартным путям. Пропиши dota_installs в config.json.")


if __name__ == "__main__":
    main()
