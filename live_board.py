"""live_board.py — Современный Live HUD 2.0 для Dota 2.
Плавный дашборд без перезагрузки страниц, живые таймеры карты, вышки, байбеки,
драфт-калькулятор и разведка лобби / смурф-радар.
Запуск: python live_board.py -> http://127.0.0.1:8081
"""
import io
import json
import os
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
except Exception:
    pass

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import dota_core as C
import draft_engine
import live_data as D
import scout_engine
import auto_scout

HOST = "127.0.0.1"
PORT = 8081
try:
    PORT = int(C.CFG.get("live_board_port", 8081))
except Exception:
    pass


HTML_PAGE = """<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Dota 2 Live HUD 2.0</title>
  <style>
    :root {
      --bg: #090c10;
      --card-bg: rgba(22, 27, 34, 0.85);
      --card-border: #30363d;
      --text: #e6edf3;
      --text-muted: #8b949e;
      --radiant: #2dd4bf;
      --dire: #f43f5e;
      --gold: #fbbf24;
      --mana: #38bdf8;
      --hp: #10b981;
      --accent: #818cf8;
      --danger: #ef4444;
      --warning: #f59e0b;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--bg);
      background-image: radial-gradient(circle at 50% 0%, #171d29 0%, #090c10 70%);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      min-height: 100vh;
      padding: 20px;
    }
    .container { max-width: 1200px; margin: 0 auto; display: flex; flex-direction: column; gap: 16px; }
    
    /* Header */
    .header-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 16px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      backdrop-filter: blur(8px);
    }
    .match-info h1 { font-size: 22px; font-weight: 700; display: flex; align-items: center; gap: 10px; }
    .badge {
      display: inline-block;
      padding: 3px 10px;
      border-radius: 20px;
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
      background: #21262d;
      border: 1px solid var(--card-border);
    }
    .badge-live { background: rgba(16, 185, 129, 0.2); border-color: #10b981; color: #10b981; }
    .badge-stale { background: rgba(244, 63, 94, 0.2); border-color: #f43f5e; color: #f43f5e; }
    .badge-danger { background: rgba(239, 68, 68, 0.25); border-color: #ef4444; color: #f87171; animation: pulse-danger 2s infinite; }
    .badge-warn { background: rgba(245, 158, 11, 0.25); border-color: #f59e0b; color: #fbbf24; }
    .badge-norm { background: rgba(16, 185, 129, 0.2); border-color: #10b981; color: #34d399; }
    .badge-tilt { background: rgba(56, 189, 248, 0.2); border-color: #38bdf8; color: #38bdf8; }

    @keyframes pulse-danger {
      0%, 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
      50% { box-shadow: 0 0 10px 2px rgba(239, 68, 68, 0.6); }
    }
    
    .score-banner {
      display: flex;
      align-items: center;
      gap: 20px;
      font-size: 32px;
      font-weight: 800;
      font-variant-numeric: tabular-nums;
    }
    .score-rad { color: var(--radiant); }
    .score-dire { color: var(--dire); }
    .clock-box { font-size: 20px; color: var(--gold); text-align: center; }
    
    /* Grid */
    .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
    .grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
    @media (max-width: 850px) { .grid-2, .grid-3 { grid-template-columns: 1fr; } }
    
    .card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 16px;
      backdrop-filter: blur(8px);
    }
    .card-title {
      font-size: 14px;
      font-weight: 600;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    /* Hero Card */
    .hero-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
    .hero-name { font-size: 20px; font-weight: 700; color: #fff; }
    .hero-level { color: var(--gold); font-size: 14px; font-weight: 600; }
    .bar-container { margin-bottom: 8px; }
    .bar-label { display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 3px; font-weight: 600; }
    .bar-bg { width: 100%; height: 12px; background: #21262d; border-radius: 6px; overflow: hidden; }
    .bar-fill-hp { height: 100%; background: linear-gradient(90deg, #059669, #10b981); transition: width 0.3s ease; }
    .bar-fill-mp { height: 100%; background: linear-gradient(90deg, #0284c7, #38bdf8); transition: width 0.3s ease; }
    
    .stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-top: 14px; }
    .stat-pill { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 8px; text-align: center; }
    .stat-val { font-size: 16px; font-weight: 700; color: #fff; }
    .stat-desc { font-size: 11px; color: var(--text-muted); margin-top: 2px; }

    /* Timers */
    .timer-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 10px 12px;
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 8px;
      margin-bottom: 8px;
    }
    .timer-name { font-weight: 600; font-size: 14px; display: flex; align-items: center; gap: 8px; }
    .timer-val { font-family: monospace; font-size: 15px; font-weight: 700; color: var(--gold); }
    
    /* Buildings */
    .team-bld { padding: 10px; border-radius: 8px; margin-bottom: 8px; }
    .bld-rad { background: rgba(45, 212, 191, 0.08); border-left: 4px solid var(--radiant); }
    .bld-dire { background: rgba(244, 63, 94, 0.08); border-left: 4px solid var(--dire); }
    .bld-row { display: flex; justify-content: space-between; font-size: 13px; margin-top: 4px; }

    /* Events */
    .event-feed { max-height: 160px; overflow-y: auto; font-size: 13px; display: flex; flex-direction: column; gap: 6px; }
    .event-item { padding: 6px 10px; background: #161b22; border-radius: 6px; border-left: 3px solid var(--accent); }

    /* Input & Buttons */
    .draft-box { display: flex; gap: 10px; margin-bottom: 12px; flex-wrap: wrap; }
    .draft-input {
      flex: 1;
      min-width: 250px;
      background: #0d1117;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 10px 14px;
      color: #fff;
      font-size: 14px;
    }
    .draft-btn {
      background: #4f46e5;
      color: #fff;
      border: none;
      border-radius: 8px;
      padding: 10px 18px;
      font-weight: 600;
      cursor: pointer;
      transition: background 0.2s;
    }
    .draft-btn:hover { background: #4338ca; }
    .draft-results { font-size: 13px; }

    /* Scout Cards Grid */
    .scout-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(270px, 1fr)); gap: 12px; margin-top: 10px; }
    .scout-card {
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 10px;
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 6px;
      position: relative;
    }
    .scout-card-header { display: flex; justify-content: space-between; align-items: flex-start; }
    .scout-card-name { font-weight: 700; font-size: 15px; color: #fff; }
    .scout-card-rank { font-size: 12px; color: var(--gold); }
    .hero-chip {
      display: inline-block;
      padding: 2px 7px;
      background: #21262d;
      border: 1px solid #30363d;
      border-radius: 5px;
      font-size: 11px;
      margin-right: 4px;
      margin-top: 3px;
    }
    .hero-chip-good { border-color: rgba(16, 185, 129, 0.4); color: #34d399; }
    .hero-chip-bad { border-color: rgba(244, 63, 94, 0.4); color: #f87171; }

    /* Auto Scout & Teams Grid */
    .teams-container {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
      margin-top: 12px;
    }
    @media (max-width: 960px) {
      .teams-container { grid-template-columns: 1fr; }
    }
    .team-column {
      background: rgba(22, 27, 34, 0.7);
      border: 1px solid #30363d;
      border-radius: 12px;
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .team-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 8px;
      border-bottom: 1px solid #30363d;
      margin-bottom: 4px;
    }
    .team-title-rad {
      font-size: 15px;
      font-weight: 700;
      color: var(--radiant);
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .team-title-dire {
      font-size: 15px;
      font-weight: 700;
      color: var(--dire);
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .team-title-un {
      font-size: 15px;
      font-weight: 700;
      color: #94a3b8;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .player-card {
      background: #0d1117;
      border: 1px solid #30363d;
      border-radius: 8px;
      padding: 10px 12px;
      display: flex;
      flex-direction: column;
      gap: 6px;
      position: relative;
      transition: all 0.2s ease;
    }
    .player-card:hover { border-color: #58a6ff; }
    .card-danger { border-left: 4px solid #f43f5e !important; }
    .card-warn { border-left: 4px solid #f59e0b !important; }
    .card-tilt { border-left: 4px solid #38bdf8 !important; }
    .card-normal { border-left: 4px solid #10b981 !important; }
    .card-you {
      border: 1px solid #6366f1 !important;
      background: linear-gradient(180deg, rgba(99, 102, 241, 0.12), #0d1117) !important;
    }
    .player-row-top {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 8px;
    }
    .player-profile-left {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .player-avatar {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      border: 1px solid #30363d;
      object-fit: cover;
      background: #21262d;
    }
    .player-name-text {
      font-size: 14px;
      font-weight: 700;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 6px;
      flex-wrap: wrap;
    }
    .player-sub-text {
      font-size: 11px;
      color: var(--text-muted);
    }
    .player-sub-text a {
      color: var(--gold);
      text-decoration: none;
    }
    .player-sub-text a:hover {
      text-decoration: underline;
    }
    .hero-picked-tag {
      display: inline-block;
      font-size: 11px;
      font-weight: 600;
      color: #e2e8f0;
      background: #1e293b;
      padding: 2px 6px;
      border-radius: 4px;
    }
    .stats-summary {
      font-size: 12px;
      color: #cbd5e1;
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }
    .chips-container {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
      margin-top: 2px;
    }
    .tactical-box {
      font-size: 11px;
      color: #a5b4fc;
      background: rgba(99, 102, 241, 0.1);
      border-left: 2px solid #818cf8;
      border-radius: 3px;
      padding: 4px 8px;
      margin-top: 2px;
    }
    .alert-banner {
      background: rgba(244, 63, 94, 0.12);
      border: 1px solid rgba(244, 63, 94, 0.5);
      border-radius: 8px;
      padding: 10px 14px;
      margin-bottom: 12px;
      color: #fecdd3;
      font-size: 13px;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .badge-danger-pulse {
      animation: pulseDanger 2s infinite;
    }
    @keyframes pulseDanger {
      0% { box-shadow: 0 0 0 0 rgba(244, 63, 94, 0.6); }
      70% { box-shadow: 0 0 0 7px rgba(244, 63, 94, 0); }
      100% { box-shadow: 0 0 0 0 rgba(244, 63, 94, 0); }
    }
  </style>
</head>
<body>
  <div class="container">
    <!-- Header -->
    <div class="header-card">
      <div class="match-info">
        <h1>
          <span>🛡️ Dota 2 Live Tracker</span>
          <span id="badge-status" class="badge badge-stale">Ожидание GSI</span>
        </h1>
        <div style="font-size: 13px; color: var(--text-muted); margin-top: 4px;">
          Матч: <span id="match-id" style="color: #fff;">0</span> | Стадия: <span id="game-stage" style="color: #fff;">-</span>
        </div>
      </div>
      <div class="score-banner">
        <span class="score-rad" id="score-radiant">0</span>
        <div class="clock-box">
          <div id="game-clock">00:00</div>
          <div style="font-size: 11px; color: var(--text-muted);" id="day-night-icon">☀️ День</div>
        </div>
        <span class="score-dire" id="score-dire">0</span>
      </div>
    </div>

    <!-- Main Grid -->
    <div class="grid-2">
      <!-- Player Status -->
      <div class="card">
        <div class="card-title">
          <span>Твой Герой</span>
          <span id="bb-status" class="badge">Байбек: ?</span>
        </div>
        <div class="hero-header">
          <div>
            <div class="hero-name" id="hero-name">Ожидание выбора...</div>
            <div style="font-size: 13px; color: var(--text-muted);" id="player-name">Игрок</div>
          </div>
          <div class="hero-level" id="hero-lvl">Уровень -</div>
        </div>

        <div class="bar-container">
          <div class="bar-label"><span>Здоровье</span><span id="hp-text">0 / 0</span></div>
          <div class="bar-bg"><div class="bar-fill-hp" id="hp-bar" style="width: 0%;"></div></div>
        </div>
        <div class="bar-container">
          <div class="bar-label"><span>Мана</span><span id="mp-text">0 / 0</span></div>
          <div class="bar-bg"><div class="bar-fill-mp" id="mp-bar" style="width: 0%;"></div></div>
        </div>

        <div class="stats-row">
          <div class="stat-pill"><div class="stat-val" id="kda-val">0/0/0</div><div class="stat-desc">KDA</div></div>
          <div class="stat-pill"><div class="stat-val" id="cs-val">0/0</div><div class="stat-desc">LH / DN</div></div>
          <div class="stat-pill"><div class="stat-val" style="color: var(--gold);" id="gold-val">0</div><div class="stat-desc">Золото</div></div>
          <div class="stat-pill"><div class="stat-val" id="gpm-val">0</div><div class="stat-desc">GPM / XPM</div></div>
        </div>
      </div>

      <!-- Map Timers -->
      <div class="card">
        <div class="card-title">Тайминги карты</div>
        <div class="timer-item">
          <div class="timer-name">🪷 Лотусы (каждые 3 мин)</div>
          <div class="timer-val" id="timer-lotus">--:--</div>
        </div>
        <div class="timer-item">
          <div class="timer-name">📜 Руна мудрости (каждые 7 мин)</div>
          <div class="timer-val" id="timer-wisdom">--:--</div>
        </div>
        <div class="timer-item">
          <div class="timer-name">🗿 Торментор (20:00)</div>
          <div class="timer-val" id="timer-tormentor">--:--</div>
        </div>
        <div class="timer-item">
          <div class="timer-name" id="cycle-label">☀️ До смены дня/ночи</div>
          <div class="timer-val" id="timer-cycle">--:--</div>
        </div>
      </div>
    </div>

    <!-- Secondary Grid: Tempo, Buildings, Events -->
    <div class="grid-3">
      <!-- Tempo -->
      <div class="card">
        <div class="card-title">Темп фарма (Факт GPM)</div>
        <div style="font-size: 13px; color: var(--text-muted); margin-bottom: 12px;">Реальный прирост золота в минуту</div>
        <div class="timer-item">
          <div class="timer-name">За 1 минуту:</div>
          <div class="timer-val" id="tempo-1m">-</div>
        </div>
        <div class="timer-item">
          <div class="timer-name">За 5 минут:</div>
          <div class="timer-val" id="tempo-5m">-</div>
        </div>
        <div style="margin-top: 10px; font-size: 13px; color: #a5b4fc;" id="tempo-verdict"></div>
      </div>

      <!-- Buildings -->
      <div class="card">
        <div class="card-title">Состояние базы</div>
        <div class="team-bld bld-rad">
          <strong style="color: var(--radiant);">Radiant:</strong>
          <div class="bld-row"><span>Вышки:</span><span id="rad-towers">11 / 11</span></div>
          <div class="bld-row"><span>Бараки:</span><span id="rad-rax">6 / 6</span></div>
        </div>
        <div class="team-bld bld-dire">
          <strong style="color: var(--dire);">Dire:</strong>
          <div class="bld-row"><span>Вышки:</span><span id="dire-towers">11 / 11</span></div>
          <div class="bld-row"><span>Бараки:</span><span id="dire-rax">6 / 6</span></div>
        </div>
      </div>

      <!-- Events -->
      <div class="card">
        <div class="card-title">Лента событий</div>
        <div class="event-feed" id="event-feed">
          <div class="event-item">Ожидание событий матча...</div>
        </div>
      </div>
    </div>

    <!-- Scout & Smurf Radar Panel -->
    <div class="card">
      <div class="card-title">
        <span>⚔️ Радар Лобби: Союзники vs Противники (Pick Phase & Live Scout)</span>
        <span class="badge" id="lobby-status-badge" style="background: rgba(16, 185, 129, 0.15); border-color: #10b981; color: #34d399;">📡 Авто-поиск активен</span>
      </div>
      <div style="font-size: 13px; color: var(--text-muted); margin-bottom: 12px;">
        Автоматическое обнаружение всех игроков во время выбора героев: проверка на смурфа/бустера, винрейт, недавний пул и советы по банам (0 кликов, 100% VAC-Safe).
      </div>

      <!-- Alert Banner if threats detected -->
      <div id="threat-alert-banner" class="alert-banner" style="display: none;"></div>

      <!-- Two Teams Grid (Radiant vs Dire) -->
      <div id="auto-teams-container">
        <div style="color: var(--text-muted); padding: 16px; text-align: center; background: #161b22; border-radius: 8px;">
          ⏳ Ожидание лобби... Радар слушает GSI, консоль и буфер обмена в реальном времени.<br>
          <span style="font-size: 11px; color: #8b949e;">Как только начнется стадия выбора героев, выписки по союзникам и противникам появятся здесь автоматически.</span>
        </div>
      </div>

      <!-- Collapsible Manual & Clipboard Tools -->
      <details style="margin-top: 14px; font-size: 12px; color: var(--text-muted);">
        <summary style="cursor: pointer; color: #818cf8; font-weight: 600;">➕ Ручной поиск / проверка чужого ID или ссылки</summary>
        <div class="draft-box" style="margin-top: 10px;">
          <input type="text" id="scout-input" class="draft-input" placeholder="Введи Account ID, SteamID64, ссылки OpenDota/Dotabuff или вставь текст...">
          <button class="draft-btn" style="background: #2563eb;" onclick="runScout()">Просканировать</button>
          <button class="draft-btn" style="background: #374151;" onclick="scoutSelf()">Мой профиль</button>
        </div>
        <div id="scout-output"></div>
      </details>
    </div>

    <!-- Draft Counter Tool Inline -->
    <div class="card">
      <div class="card-title">🎯 Интерактивный контрпик (Все 124+ героя)</div>
      <div class="draft-box">
        <input type="text" id="draft-input" class="draft-input" placeholder="Введи врагов через пробел (напр: sniper pudge pa или сф од)">
        <button class="draft-btn" onclick="calcDraft()">Рассчитать</button>
      </div>
      <div id="draft-output" class="draft-results" style="display: none;"></div>
    </div>

  </div>

  <script>
    function fmtClock(sec) {
      if (sec === null || sec === undefined) return "00:00";
      sec = Math.floor(sec);
      const m = Math.floor(sec / 60);
      const s = Math.abs(sec % 60);
      return (sec < 0 ? "-" : "") + m + ":" + (s < 10 ? "0" : "") + s;
    }

    async function updateBoard() {
      try {
        const res = await fetch('/api/board');
        const b = await res.json();
        if (!b.ok) {
          document.getElementById('badge-status').textContent = 'Нет данных GSI';
          document.getElementById('badge-status').className = 'badge badge-stale';
          return;
        }

        // Status
        const age = b.gsi_age_sec;
        const isFresh = age >= 0 && age < 10;
        if (!isFresh) {
          document.getElementById('badge-status').textContent = '💤 В МЕНЮ ДОТЫ';
          document.getElementById('badge-status').className = 'badge badge-stale';
          document.getElementById('game-stage').textContent = 'В главном меню';
          document.getElementById('game-clock').textContent = '--:--';
          document.getElementById('match-id').textContent = '-';
          document.getElementById('score-radiant').textContent = '-';
          document.getElementById('score-dire').textContent = '-';
          document.getElementById('hero-name').textContent = 'Вне матча';
          document.getElementById('player-name').textContent = 'Ожидание выбора героев / матча...';
          document.getElementById('hero-lvl').textContent = '';
          document.getElementById('hp-text').textContent = '- / -';
          document.getElementById('hp-bar').style.width = '0%';
          document.getElementById('mp-text').textContent = '- / -';
          document.getElementById('mp-bar').style.width = '0%';
          document.getElementById('kda-val').textContent = '-/-/-';
          document.getElementById('cs-val').textContent = '- / -';
          document.getElementById('gold-val').textContent = '-';
          document.getElementById('gpm-val').textContent = '- / -';
          document.getElementById('bb-status').textContent = '⚪ Вне матча';
          document.getElementById('bb-status').style.color = 'var(--text-muted)';
          document.getElementById('timer-lotus').textContent = '--:--';
          document.getElementById('timer-wisdom').textContent = '--:--';
          document.getElementById('timer-tormentor').textContent = 'Старт на 20:00';
          document.getElementById('timer-cycle').textContent = '--:--';
          document.getElementById('tempo-1m').textContent = '-';
          document.getElementById('tempo-5m').textContent = '-';
          document.getElementById('tempo-verdict').textContent = '';
          if (b.lobby_scout) {
            updateLobbyDisplay(b.lobby_scout);
          }
          return;
        }
        document.getElementById('badge-status').textContent = isFresh ? 'LIVE' : 'GSI ' + age + 'с';
        document.getElementById('badge-status').className = 'badge ' + (isFresh ? 'badge-live' : 'badge-stale');
        
        document.getElementById('match-id').textContent = b.match_id || '0';
        document.getElementById('game-stage').textContent = b.stage || '-';
        document.getElementById('game-clock').textContent = fmtClock(b.clock);
        
        // Score
        const sc = b.score || {};
        document.getElementById('score-radiant').textContent = sc.radiant || 0;
        document.getElementById('score-dire').textContent = sc.dire || 0;

        // Player
        const u = b.you || {};
        document.getElementById('hero-name').textContent = u.hero_name || 'Герой';
        document.getElementById('player-name').textContent = (u.name || 'Игрок') + (u.team ? ' (' + u.team + ')' : '');
        document.getElementById('hero-lvl').textContent = 'Уровень ' + (u.level || 1);
        
        const hp = u.health || 0;
        const maxHp = u.max_health || 1;
        document.getElementById('hp-text').textContent = hp + ' / ' + maxHp;
        document.getElementById('hp-bar').style.width = Math.min(100, Math.max(0, (hp / maxHp) * 100)) + '%';

        const mp = u.mana || 0;
        const maxMp = u.max_mana || 1;
        document.getElementById('mp-text').textContent = mp + ' / ' + maxMp;
        document.getElementById('mp-bar').style.width = Math.min(100, Math.max(0, (mp / maxMp) * 100)) + '%';

        document.getElementById('kda-val').textContent = u.kda || '0/0/0';
        document.getElementById('cs-val').textContent = (u.lh || 0) + ' / ' + (u.denies || 0);
        document.getElementById('gold-val').textContent = u.gold || 0;
        document.getElementById('gpm-val').textContent = (u.gpm_gsi || 0) + ' / ' + (u.xpm_gsi || 0);

        // Buyback status
        const bbBadge = document.getElementById('bb-status');
        if (u.has_buyback) {
          bbBadge.textContent = '🟢 Байбек готов';
          bbBadge.style.color = '#10b981';
        } else if (u.buyback_cooldown > 0) {
          bbBadge.textContent = '⏳ Байбек КД (' + u.buyback_cooldown + 'с)';
          bbBadge.style.color = '#fbbf24';
        } else {
          bbBadge.textContent = '🔴 Нет байбека (' + u.gold + '/' + u.buyback_cost + ')';
          bbBadge.style.color = '#f43f5e';
        }

        // Timers
        const t = b.timers || {};
        document.getElementById('timer-lotus').textContent = t.lotus_fmt || '--:--';
        document.getElementById('timer-wisdom').textContent = t.wisdom_fmt || '--:--';
        document.getElementById('timer-tormentor').textContent = t.tormentor_status || '--:--';
        document.getElementById('timer-cycle').textContent = t.day_night_fmt || '--:--';
        document.getElementById('cycle-label').textContent = (t.is_day ? '☀️' : '🌙') + ' До смены ' + (t.is_day ? 'ночи' : 'дня');
        document.getElementById('day-night-icon').textContent = (t.is_day ? '☀️ День' : '🌙 Ночь');

        // Tempo
        const tempo = b.tempo || {};
        const t1 = (tempo['60сек'] || {})['золото_в_мин_факт'];
        const t5 = (tempo['5мин'] || {})['золото_в_мин_факт'];
        document.getElementById('tempo-1m').textContent = t1 !== undefined ? (t1 > 0 ? '+' : '') + t1 + ' /мин' : '-';
        document.getElementById('tempo-5m').textContent = t5 !== undefined ? (t5 > 0 ? '+' : '') + t5 + ' /мин' : '-';
        
        let verdict = '';
        if (t5 !== undefined) {
          if (t5 < 300) verdict = '⚠️ Темп фарма низкий, ускорь фарм или стаки';
          else if (t5 > 550) verdict = '🔥 Отличный темп, развивай доминацию!';
        }
        document.getElementById('tempo-verdict').textContent = verdict;

        // Buildings
        const bld = b.buildings || {};
        const radBld = bld.radiant || {};
        const direBld = bld.dire || {};
        document.getElementById('rad-towers').textContent = (radBld.towers_alive !== undefined ? radBld.towers_alive : 11) + ' / 11';
        document.getElementById('rad-rax').textContent = (radBld.rax_alive !== undefined ? radBld.rax_alive : 6) + ' / 6';
        document.getElementById('dire-towers').textContent = (direBld.towers_alive !== undefined ? direBld.towers_alive : 11) + ' / 11';
        document.getElementById('dire-rax').textContent = (direBld.rax_alive !== undefined ? direBld.rax_alive : 6) + ' / 6';

        // Events
        const evList = b.events || [];
        if (evList.length > 0) {
          document.getElementById('event-feed').innerHTML = evList.map(e => '<div class="event-item">' + e + '</div>').join('');
        }

        // Auto Lobby Scout
        if (b.lobby_scout) {
          updateLobbyDisplay(b.lobby_scout);
        }
      } catch (err) {
        console.error('Update error:', err);
      }
    }

    async function calcDraft() {
      const inp = document.getElementById('draft-input').value.trim();
      if (!inp) return;
      const out = document.getElementById('draft-output');
      out.style.display = 'block';
      out.innerHTML = '<div style="color: var(--gold)">Выполняю расчет контрпиков...</div>';
      try {
        const res = await fetch('/api/draft?enemies=' + encodeURIComponent(inp));
        const data = await res.json();
        if (!data.ok) {
          out.innerHTML = '<div style="color: var(--dire)">' + (data.error || 'Ошибка') + '</div>';
          return;
        }
        let html = '<div style="margin-top: 10px; padding: 12px; background: #161b22; border-radius: 8px;">';
        html += '<strong style="color: #fff; font-size: 15px;">Против: ' + data.enemies.join(', ') + '</strong><br>';
        
        if (data.analysis && data.analysis.warnings && data.analysis.warnings.length) {
          html += '<div style="margin: 8px 0; color: #fbbf24;">' + data.analysis.warnings.join('<br>') + '</div>';
        }
        if (data.analysis && data.analysis.recommended_items && data.analysis.recommended_items.length) {
          html += '<div style="margin-bottom: 8px; color: #818cf8;">🎒 Рекомендуемые артефакты: ' + data.analysis.recommended_items.join(', ') + '</div>';
        }
        html += '<div style="font-weight: 700; margin: 8px 0 4px 0;">👑 Топ-5 контрпиков:</div>';
        html += '<ol style="padding-left: 20px;">';
        (data.top_counters || []).slice(0, 5).forEach(c => {
          html += '<li><strong>' + c.hero + '</strong> (' + c.role + ') — Преимущество: <span style="color: #10b981;">' + c.advantage + '</span> (WR ' + c.winrate + ')</li>';
        });
        html += '</ol></div>';
        out.innerHTML = html;
      } catch (err) {
        out.innerHTML = '<div style="color: var(--dire)">Сетевая ошибка расчета</div>';
      }
    }

    async function runScout() {
      const inp = document.getElementById('scout-input').value.trim();
      if (!inp) return;
      const out = document.getElementById('scout-output');
      out.innerHTML = '<div style="color: var(--gold); padding: 10px;">🔍 Сканирую игроков лобби и проверяю смурфов...</div>';
      try {
        const res = await fetch('/api/scout?players=' + encodeURIComponent(inp));
        const data = await res.json();
        if (!data.ok) {
          out.innerHTML = '<div style="color: var(--dire); padding: 10px;">' + (data.error || 'Ошибка сканирования') + '</div>';
          return;
        }

        let html = '<div class="scout-grid">';
        data.players.forEach(p => {
          if (!p.ok) {
            html += '<div class="scout-card" style="border-color: #f43f5e;"><strong style="color: #f87171;">ID ' + p.account_id + '</strong><div style="font-size: 12px; color: #8b949e;">' + (p.error || 'Профиль закрыт') + '</div></div>';
            return;
          }
          const v = p.smurf_verdict || {};
          const s = p.recent_summary || {};
          
          let bClass = 'badge-norm';
          if (v.class === 'danger') bClass = 'badge-danger';
          else if (v.class === 'warning') bClass = 'badge-warn';
          else if (v.class === 'tilt') bClass = 'badge-tilt';

          html += '<div class="scout-card">';
          html += '<div class="scout-card-header">';
          html += '<div><div class="scout-card-name">' + p.name + '</div><div class="scout-card-rank">' + p.rank_name + ' (ID: ' + p.account_id + ')</div></div>';
          html += '<span class="badge ' + bClass + '">' + v.badge + '</span>';
          html += '</div>';

          html += '<div style="font-size: 13px; color: #e6edf3; margin-top: 4px;">';
          html += 'Форма: <strong>' + s.wins + 'W - ' + s.losses + 'L</strong> (' + s.winrate_pct + '% WR) | KDA: ' + s.avg_kda;
          html += '</div>';

          html += '<div style="margin-top: 4px;">';
          (p.recent_heroes || []).slice(0, 3).forEach(h => {
            const hClass = h.winrate_pct >= 60 ? 'hero-chip-good' : (h.winrate_pct <= 40 ? 'hero-chip-bad' : '');
            html += '<span class="hero-chip ' + hClass + '">' + h.hero_name + ' ' + h.winrate_pct + '% (' + h.games + ')</span>';
          });
          html += '</div>';

          if (v.triggers && v.triggers.length > 0) {
            html += '<div style="font-size: 11px; color: #f59e0b; margin-top: 4px;">' + v.triggers.join('<br>') + '</div>';
          }
          if (v.tips && v.tips.length > 0) {
            html += '<div style="font-size: 11px; color: #818cf8; margin-top: 4px;">💡 ' + v.tips.join('<br>') + '</div>';
          }

          html += '</div>';
        });
        html += '</div>';
        out.innerHTML = html;
      } catch (err) {
        out.innerHTML = '<div style="color: var(--dire); padding: 10px;">Ошибка связи с сервером разведки</div>';
      }
    }

    function scoutSelf() {
      document.getElementById('scout-input').value = '1092348748';
      runScout();
    }

    function escapeHtml(str) {
      if (!str) return '';
      return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function renderPlayerCard(p) {
      const v = p.smurf_verdict || {};
      const s = p.recent_summary || {};
      const isYou = p.is_you;

      let cardClass = 'player-card';
      if (isYou) cardClass += ' card-you';
      else if (v.class === 'danger') cardClass += ' card-danger';
      else if (v.class === 'warning') cardClass += ' card-warn';
      else if (v.class === 'tilt') cardClass += ' card-tilt';
      else cardClass += ' card-normal';

      let badgeClass = 'badge-norm';
      if (v.class === 'danger') badgeClass = 'badge-danger badge-danger-pulse';
      else if (v.class === 'warning') badgeClass = 'badge-warn';
      else if (v.class === 'tilt') badgeClass = 'badge-tilt';

      const avatarSrc = p.avatar || 'https://avatars.steamstatic.com/fef49e7fa7e1997310d705b2a6158ff8dc1cdfeb_full.jpg';
      const heroBadge = p.hero_name ? `<span class="hero-picked-tag">⚔️ ${escapeHtml(p.hero_name)}</span>` : '';
      const youBadge = isYou ? '<span class="badge" style="background: #4f46e5; color: #fff; margin-left: 4px;">ТЫ</span>' : '';

      let html = `<div class="${cardClass}">`;
      html += `  <div class="player-row-top">`;
      html += `    <div class="player-profile-left">`;
      html += `      <img src="${avatarSrc}" class="player-avatar" alt="avatar" onerror="this.src='https://avatars.steamstatic.com/fef49e7fa7e1997310d705b2a6158ff8dc1cdfeb_full.jpg'">`;
      html += `      <div class="player-name-box">`;
      html += `        <div class="player-name-text">${escapeHtml(p.name || 'Player')} ${youBadge} ${heroBadge}</div>`;
      html += `        <div class="player-sub-text">${escapeHtml(p.rank_name || 'Unranked')} | ID: <a href="https://www.opendota.com/players/${p.account_id}" target="_blank">${p.account_id}</a></div>`;
      html += `      </div>`;
      html += `    </div>`;
      html += `    <span class="badge ${badgeClass}">${escapeHtml(v.badge || '🟢 ОБЫЧНЫЙ')}</span>`;
      html += `  </div>`;

      if (p.scouted && s.matches_analyzed) {
        html += `  <div class="stats-summary">`;
        html += `    <span>Форма: <strong>${s.wins}W - ${s.losses}L (${s.winrate_pct}% WR)</strong></span>`;
        html += `    <span>KDA: <strong>${s.avg_kda}</strong></span>`;
        html += `    <span>GPM: <strong>${s.avg_gpm}</strong></span>`;
        html += `  </div>`;

        if (p.recent_heroes && p.recent_heroes.length > 0) {
          html += `  <div class="chips-container">`;
          p.recent_heroes.slice(0, 3).forEach(h => {
            const hClass = h.winrate_pct >= 60 ? 'hero-chip-good' : (h.winrate_pct <= 40 ? 'hero-chip-bad' : '');
            const fire = h.is_smurf_hero ? '🔥 ' : '';
            html += `<span class="hero-chip ${hClass}" title="${h.games} игр, ${h.winrate_pct}% побед">${fire}${escapeHtml(h.hero_name)} ${h.winrate_pct}% (${h.games})</span>`;
          });
          html += `  </div>`;
        }

        if (v.triggers && v.triggers.length > 0) {
          html += `  <div style="font-size: 11px; color: #f59e0b; margin-top: 3px;">${escapeHtml(v.triggers[0])}</div>`;
        }
        if (v.tips && v.tips.length > 0) {
          html += `  <div class="tactical-box">💡 ${escapeHtml(v.tips[0])}</div>`;
        }
      } else if (!p.scouted) {
        html += `  <div style="font-size: 12px; color: var(--text-muted); font-style: italic;">${escapeHtml(p.error || 'Сканирование профиля...')}</div>`;
      }

      html += `</div>`;
      return html;
    }

    function updateLobbyDisplay(lobby) {
      if (!lobby) return;
      const rad = lobby.radiant || [];
      const dire = lobby.dire || [];
      const unassigned = lobby.unassigned || [];
      const total = lobby.total_players || 0;

      const badge = document.getElementById('lobby-status-badge');
      if (badge) {
        if (total > 0) {
          badge.textContent = '🟢 В лобби: ' + total + ' игроков';
          badge.style.borderColor = '#10b981';
          badge.style.color = '#34d399';
        } else {
          badge.textContent = '📡 Авто-поиск активен';
          badge.style.borderColor = '#818cf8';
          badge.style.color = '#818cf8';
        }
      }

      // Threat alert banner
      const banner = document.getElementById('threat-alert-banner');
      if (banner) {
        const summ = lobby.summary || {};
        if (summ.enemy_smurfs_detected > 0 || (summ.suggested_bans && summ.suggested_bans.length > 0)) {
          let bHtml = '<div style="font-size: 20px;">🚨</div><div>';
          if (summ.enemy_smurfs_detected > 0) {
            bHtml += '<strong>ВНИМАНИЕ: Во вражеской команде обнаружено опасных игроков/смурфов: ' + summ.enemy_smurfs_detected + '!</strong><br>';
          }
          if (summ.suggested_bans && summ.suggested_bans.length > 0) {
            bHtml += '<span style="font-size: 12px; color: #fed7aa;">Совет по банам: ' + escapeHtml(summ.suggested_bans.join(' | ')) + '</span>';
          }
          bHtml += '</div>';
          banner.innerHTML = bHtml;
          banner.style.display = 'flex';
        } else {
          banner.style.display = 'none';
        }
      }

      // Teams grid
      const container = document.getElementById('auto-teams-container');
      if (!container) return;

      if (rad.length === 0 && dire.length === 0 && unassigned.length === 0) {
        container.innerHTML = '<div style="color: var(--text-muted); padding: 16px; text-align: center; background: #161b22; border-radius: 8px;">⏳ Ожидание лобби... Радар слушает GSI, консоль и буфер обмена в реальном времени.<br><span style="font-size: 11px; color: #8b949e;">Как только начнется стадия выбора героев, выписки по союзникам и противникам появятся здесь автоматически.</span></div>';
        return;
      }

      let html = '<div class="teams-container">';

      // Radiant
      html += '<div class="team-column" style="border-left: 4px solid var(--radiant);">';
      html += '  <div class="team-header">';
      html += '    <div class="team-title-rad">🟢 RADIANT (' + rad.length + ' игр.)</div>';
      html += '    <span style="font-size: 11px; color: var(--text-muted);">Свет</span>';
      html += '  </div>';
      if (rad.length === 0) {
        html += '  <div style="color: var(--text-muted); font-size: 12px; font-style: italic; padding: 10px;">Ожидание игроков Radiant...</div>';
      } else {
        rad.forEach(p => { html += renderPlayerCard(p); });
      }
      html += '</div>';

      // Dire
      html += '<div class="team-column" style="border-left: 4px solid var(--dire);">';
      html += '  <div class="team-header">';
      html += '    <div class="team-title-dire">🔴 DIRE (' + dire.length + ' игр.)</div>';
      html += '    <span style="font-size: 11px; color: var(--text-muted);">Тьма</span>';
      html += '  </div>';
      if (dire.length === 0) {
        html += '  <div style="color: var(--text-muted); font-size: 12px; font-style: italic; padding: 10px;">Ожидание игроков Dire...</div>';
      } else {
        dire.forEach(p => { html += renderPlayerCard(p); });
      }
      html += '</div>';

      html += '</div>';

      // Unassigned
      if (unassigned.length > 0) {
        html += '<div class="team-column" style="margin-top: 12px; border-left: 4px solid #94a3b8;">';
        html += '  <div class="team-header">';
        html += '    <div class="team-title-un">⚪ Обнаруженные игроки лобби (' + unassigned.length + ')</div>';
        html += '    <span style="font-size: 11px; color: var(--text-muted);">Команда уточняется</span>';
        html += '  </div>';
        html += '  <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 10px;">';
        unassigned.forEach(p => { html += renderPlayerCard(p); });
        html += '  </div>';
        html += '</div>';
      }

      container.innerHTML = html;
    }

    setInterval(updateBoard, 1500);
    updateBoard();
  </script>
</body>
</html>
"""


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="text/html; charset=utf-8"):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/board":
            self._send(200, json.dumps(D.get_board(), ensure_ascii=False), "application/json; charset=utf-8")
            return

        if path == "/api/draft":
            qs = urllib.parse.parse_qs(parsed.query)
            enemies = qs.get("enemies", [""])[0]
            res = draft_engine.get_draft_advice(enemies)
            self._send(200, json.dumps(res, ensure_ascii=False), "application/json; charset=utf-8")
            return

        if path == "/api/scout":
            qs = urllib.parse.parse_qs(parsed.query)
            players_input = qs.get("players", [""])[0]
            if not players_input.strip():
                mgr = auto_scout.get_scout_manager()
                res = mgr.get_lobby_state()
            else:
                res = scout_engine.scout_lobby(players_input)
            self._send(200, json.dumps(res, ensure_ascii=False), "application/json; charset=utf-8")
            return

        if path == "/api/lobby":
            mgr = auto_scout.get_scout_manager()
            self._send(200, json.dumps(mgr.get_lobby_state(), ensure_ascii=False), "application/json; charset=utf-8")
            return

        if path in ("/", "/board", "/index.html"):
            self._send(200, HTML_PAGE)
            return

        self._send(404, "Not Found")


def main():
    C.track_tick()
    srv = HTTPServer((HOST, PORT), H)
    print("Dota 2 Live HUD 2.0 запущен: http://%s:%d" % (HOST, PORT), flush=True)
    print("Открой в браузере. Разведка лобби и смурф-радар активны.", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
