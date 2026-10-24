# dota2-mcp — Legal Dota 2 MCP Server (Analytics, Not a Bot)

A Valve Anti-Cheat (VAC) safe assistant powered by the Model Context Protocol (MCP): real-time Game State Integration (GSI) + OpenDota & STRATZ analytics + automated coach tips. Zero paid LLM token cost: runs 100% locally with free OpenDota APIs and local Python algorithmic engines.

> [!IMPORTANT]
> **100% VAC-Safe:** Does NOT automate gameplay, does NOT control the hero, does NOT inject into game memory, and does NOT intercept player inputs. Completely read-only analytics assistant.

---

## 📦 Components

- `server.py` — MCP server implementation (stdio, Python standard library only, zero pip dependencies)
- `gsi_server.py` — Local HTTP receiver for Dota 2 Game State Integration (`http://127.0.0.1:3000`)
- `auto_scout.py` — Autonomous real-time lobby scanner: multi-source player discovery (Valve GSI `allplayers`, OpenDota `/api/live`, `console.log` engine sniffer, and Windows clipboard) with 0 button clicks
- `scout_engine.py` — Draft scout & smurf radar: checks allies and opponents for smurfing/boosting indicators, recent hero pools, winrates, and tactical ban advice
- `draft_engine.py` — Full draft analysis and counter-pick engine for all 124+ heroes, with slang recognition, advantage metrics, damage/disable breakdown, and item recommendations
- `postgame_analyzer.py` — Deep post-match algorithmic analyzer (KDA ratio, kill participation, damage shares, itemization audit vs enemy lineup, mistakes and strengths)
- `live_board.py` — Modern Live HUD 2.0 web dashboard (`http://127.0.0.1:8081`): dark glassmorphism, no page reload, active map timers (Lotus, Wisdom, Tormentor, Day/Night), base buildings grid, interactive draft calculator, and hands-free team scouting radar (Radiant vs Dire)
- `DotaOverlay.Wpf/` (`overlay_bin/DotaOverlay.Wpf.exe`, `start_overlay.bat`) — Native C# .NET 9 In-Game Transparent Click-Through Overlay: zero screen darkening, DirectX-accelerated 60 FPS glassmorphism, global F8 hotkey toggle, smurf radar during pick phase, map timers and buyback tracker during match
- `live_data.py` — Live data aggregation and timer computation
- `coach_cli.py` — Interactive terminal coach with instant access to live game status, draft counter-picking, lobby scouting, and match reviews
- `config.json` — Configurable account ID, Steam/Dota installation paths, and GSI port
- `tools/install_gsi.py` — Automatic installer for the GSI configuration file into Dota 2 directories

---

## 🚀 Quick Start (Windows, PowerShell)

```powershell
cd C:\AI\dota2-mcp

# 1. Install the GSI config into your Dota 2 installation
python tools\install_gsi.py

# 2. Start the automated suite (GSI + Watcher + Live HUD 2.0)
start_auto.bat
# Or launch the Live HUD manually:
python live_board.py
# Open: http://127.0.0.1:8081

# 3. Configure your Dota numeric account ID (NOT SteamID64)
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
| `dota_gsi_latest` | Fetches live in-game metrics: hero, HP/MP, KDA, GPM/XPM, game time, timers |
| `dota_gsi_install` | Reinstalls or repairs the GSI configuration file |
| `dota_set_account` / `dota_whoami` | Sets or displays the active OpenDota account ID |
| `dota_profile` | Retrieves OpenDota profile info: estimated MMR, win rate, signature heroes |
| `dota_recent_matches` | Lists recent matches with stats, hero picks, and win/loss results |
| `dota_scout_player` | Dossier on a player: smurf risk, recent winrate, top heroes played, and ban advice |
| `dota_scout_lobby` | Scans up to 10 players in parallel from IDs, URLs, or console text |
| `dota_match_details` | Deep post-game breakdown: KDA, kill participation, damage shares, itemization audit |
| `dota_hero_stats` | Hero performance analytics and win rates |
| `dota_coach_tip` | Context-aware coaching advice for the current game state or hero |
| `dota_pick_advice` | Full draft counter-pick engine against 1–5 enemy heroes (124+ heroes, slang, item counters) |
| `dota_item_guide` | Standard item build guides (Starting → Mid → Late game) |
| `dota_stratz_match` | Advanced match data via STRATZ GraphQL (requires `STRATZ_TOKEN`) |

---

## 📄 License

MIT
