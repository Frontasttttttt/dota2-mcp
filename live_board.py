"""live_board.py — Современный Live HUD 2.0 для Dota 2.
Плавный дашборд без перезагрузки страниц, живые таймеры карты, вышки, байбеки и драфт-калькулятор.
Запуск: python live_board.py -> http://127.0.0.1:8081
"""
import io
import json
import os
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import dota_core as C
import draft_engine
import live_data as D

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

    /* Draft Counter Calculator */
    .draft-box { display: flex; gap: 10px; margin-bottom: 12px; }
    .draft-input {
      flex: 1;
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
        const isFresh = age >= 0 && age < 6;
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

        if path in ("/", "/board", "/index.html"):
            self._send(200, HTML_PAGE)
            return

        self._send(404, "Not Found")


def main():
    C.track_tick()
    srv = HTTPServer((HOST, PORT), H)
    print("Dota 2 Live HUD 2.0 запущен: http://%s:%d" % (HOST, PORT))
    print("Открой в браузере. Данные обновляются плавно без перезагрузки страницы.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
