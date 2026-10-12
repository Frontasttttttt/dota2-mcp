# dota2-mcp — Legal Dota 2 MCP Server (Analytics, Not a Bot)

A Valve Anti-Cheat (VAC) safe assistant powered by the Model Context Protocol (MCP): real-time Game State Integration (GSI) + OpenDota & STRATZ analytics + automated coach tips.

> [!IMPORTANT]
> **100% VAC-Safe:** Does NOT automate gameplay, does NOT control the hero, and does NOT intercept player inputs. Completely read-only analytics assistant.

---

## 📦 Components

- `server.py` — MCP server implementation (stdio, Python standard library only, zero pip dependencies)
- `gsi_server.py` — Local HTTP receiver for Dota 2 Game State Integration (`http://127.0.0.1:3000`)
- `coach_data.json` — Coaching knowledge base: item timings, hero matchups, power spikes, and builds
- `config.json` — Configurable account ID, Steam/Dota installation paths, and GSI port
- `tools/install_gsi.py` — Automatic installer for the GSI configuration file into Dota 2 directories

---

## 🚀 Quick Start (Windows, PowerShell)

```powershell
cd C:\AI\dota2-mcp

# 1. Install the GSI config into your Dota 2 installation
python tools\install_gsi.py

# 2. Start the local GSI receiver (keep this running while playing)
python gsi_server.py
# Verification endpoint: http://127.0.0.1:3000/status

# 3. Configure your Dota numeric account ID (NOT SteamID64)
# Find it at: https://www.opendota.com (digits in profile URL) or https://steamid.io
python server.py --set-account 123456789
```

### 4. Connect to Claude Desktop or any MCP Client

Add the following to your `claude_desktop_config.json`:

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

Restart your MCP client. All `dota_*` tools will be available immediately.

---

## 🛠️ MCP Tools Overview

| Tool | Description |
| :--- | :--- |
| `dota_launch` | Launches Dota 2 via Steam (`-applaunch 570`) with training mode instructions |
| `dota_gsi_status` | Checks GSI server heartbeat and last packet timestamp |
| `dota_gsi_latest` | Fetches live in-game metrics: hero, HP/MP, KDA, GPM/XPM, game time |
| `dota_gsi_install` | Reinstalls or repairs the GSI configuration file |
| `dota_set_account` / `dota_whoami` | Sets or displays the active OpenDota account ID |
| `dota_profile` | Retrieves OpenDota profile info: estimated MMR, win rate, signature heroes |
| `dota_recent_matches` | Lists recent matches with stats, hero picks, and win/loss results |
| `dota_match_details` | Detailed breakdown of a specific match ID |
| `dota_hero_stats` | Hero performance analytics and win rates |
| `dota_coach_tip` | Context-aware coaching advice for the current game state or hero |
| `dota_pick_advice` | Draft recommendations against 1–5 enemy heroes |
| `dota_item_guide` | Standard item build guides (Starting → Mid → Late game) |
| `dota_stratz_match` | Advanced match data via STRATZ GraphQL (requires `STRATZ_TOKEN`) |

---

## 📄 License

MIT
