import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import win32com.client

def install():
    startup_dir = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    shortcut_path = startup_dir / "Dota2_Assistant.lnk"

    pythonw_exe = Path(sys.executable).parent / "pythonw.exe"
    script_path = Path(r"c:\AI\dota2-mcp\dota_assistant.pyw")

    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(str(shortcut_path))
    shortcut.Targetpath = str(pythonw_exe)
    shortcut.Arguments = f'"{script_path}"'
    shortcut.WorkingDirectory = str(script_path.parent)
    shortcut.Description = "Dota 2 Silent Background AI Assistant"
    shortcut.save()
    print(f"[*] Готово! Ярлык автозапуска создан: {shortcut_path}")

def uninstall():
    startup_dir = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    shortcut_path = startup_dir / "Dota2_Assistant.lnk"
    if shortcut_path.exists():
        shortcut_path.unlink()
        print(f"[*] Ярлык удален из автозагрузки.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "uninstall":
        uninstall()
    else:
        install()
