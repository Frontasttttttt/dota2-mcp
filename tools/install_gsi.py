"""Установка GSI-конфига в найденные копии Dota 2."""
import json
import os
import sys

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
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg_path = os.path.join(here, "config.json")
    installs = DEFAULT_INSTALLS
    port = 3000
    try:
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
        if cfg.get("dota_installs"):
            installs = cfg["dota_installs"]
        port = int(cfg.get("gsi_port", 3000))
    except Exception:
        pass
    extra = [a for a in sys.argv[1:] if not a.startswith("-")]
    if extra:
        installs = extra
    print("GSI install, port=%d" % port)
    ok = 0
    for root in installs:
        dota_exe = os.path.join(root, "game", "bin", "win64", "dota2.exe")
        exists = os.path.exists(root)
        print(("- %s %s" % (root, "(папка есть)" if exists else "(ПАПКА НЕ НАЙДЕНА)")))
        if not exists:
            continue
        try:
            p = install_to(root, port)
            print(("  -> OK: %s" % p))
            if not os.path.exists(dota_exe):
                print("  (dota2.exe не найден по стандартному пути — но cfg положен, GSI сработает)")
            ok += 1
        except Exception as e:
            print(("  -> ОШИБКА: %s" % e))
    print("Готово: %d/%d. Теперь запусти: python gsi_server.py" % (ok, len(installs)))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
