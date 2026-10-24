"""draft_overlay.py — Прозрачный In-Game оверлей стадии выбора героев для Dota 2.
Отображает досье игроков (винрейт, недавние герои с винрейтом, смурф-метки)
прямо под аватарками союзников и противников во время Pick Phase.
- 100% VAC-Safe (чистый Windows GUI оверлей поверх экрана, 0 хуков памяти).
- Click-Through: клики мыши проходят сквозь оверлей прямо в Доту без задержек.
- Автоматически появляется при стадии HERO_SELECTION и скрывается при старте игры.
- Горячая клавиша F8: принудительно показать/скрыть в любой момент.
"""
import ctypes
import json
import os
import sys
import threading
import time
import tkinter as tk

BASE = os.path.dirname(os.path.abspath(__file__))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

import auto_scout
import dota_core as C

user32 = ctypes.windll.user32
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x80
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TRANSPARENT = 0x20
WS_EX_LAYERED = 0x80000
HWND_TOPMOST = -1
SWP_NOACTIVATE = 0x0010
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOOWNERZORDER = 0x0200
SWP_SHOWWINDOW = 0x0040
VK_F8 = 0x77


def make_clickthrough(hwnd: int):
    """Делает окно абсолютно прозрачным для кликов мыши (клики идут прямо в Доту)."""
    try:
        s = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        s |= WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE | WS_EX_TRANSPARENT | WS_EX_LAYERED
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, s)
        user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                           SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_NOOWNERZORDER | SWP_SHOWWINDOW)
    except Exception:
        pass


class DraftOverlayApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Dota 2 Draft Overlay")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.92)
        self.root.configure(bg="#000000")
        self.root.wm_attributes("-transparentcolor", "#000000")

        self.sw = self.root.winfo_screenwidth()
        self.sh = self.root.winfo_screenheight()
        self.root.geometry(f"{self.sw}x{self.sh}+0+0")

        self.is_visible = False
        self.manual_override = False
        self.last_f8_state = False
        self.card_widgets = []

        # Запускаем монитор горячих клавиш F8
        self._hotkey_thread = threading.Thread(target=self._hotkey_listener, daemon=True)
        self._hotkey_thread.start()

        # Делаем окно клик-сквозным
        self.root.after(100, lambda: make_clickthrough(self.root.winfo_id()))

        # Главный цикл обновления
        self.root.after(500, self._tick)

    def _hotkey_listener(self):
        """Слушает нажатие F8 для ручного включения/выключения оверлея."""
        while True:
            try:
                state = bool(user32.GetAsyncKeyState(VK_F8) & 0x8000)
                if state and not self.last_f8_state:
                    self.manual_override = not self.manual_override
                self.last_f8_state = state
            except Exception:
                pass
            time.sleep(0.08)

    def _get_current_stage(self):
        """Читает текущую стадию матча из gsi_latest.json или watcher_state.json."""
        try:
            p = os.path.join(BASE, "gsi_latest.json")
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    d = json.load(f)
                return (d.get("map") or {}).get("game_state", "UNKNOWN")
        except Exception:
            pass
        return "UNKNOWN"

    def _tick(self):
        try:
            stage = self._get_current_stage()
            mgr = auto_scout.get_scout_manager()
            lobby = mgr.get_lobby_state()
            total_players = lobby.get("total_players", 0)

            should_show = (
                self.manual_override or
                stage == "DOTA_GAMERULES_STATE_HERO_SELECTION" or
                (stage in ("DOTA_GAMERULES_STATE_WAIT_FOR_PLAYERS_TO_LOAD", "DOTA_GAMERULES_STATE_STRATEGY_TIME") and total_players > 0)
            )

            if should_show and not self.is_visible:
                self.root.deiconify()
                self.root.lift()
                make_clickthrough(self.root.winfo_id())
                self.is_visible = True
            elif not should_show and self.is_visible:
                self.root.withdraw()
                self.is_visible = False

            if self.is_visible:
                self._render_overlay(lobby)
        except Exception:
            pass

        self.root.after(1200, self._tick)

    def _render_overlay(self, lobby):
        """Отрисовывает плашки игроков под слотами аватарок."""
        # Очищаем старые виджеты
        for w in self.card_widgets:
            try:
                w.destroy()
            except Exception:
                pass
        self.card_widgets.clear()

        rad = lobby.get("radiant") or []
        dire = lobby.get("dire") or []

        # Демо-данные для визуального теста при ручном нажатии F8 вне матча
        if not rad and not dire and self.manual_override:
            rad = [
                {"name": "You (ТЫ)", "rank_name": "Ancient 3", "scouted": True, "recent_summary": {"matches_analyzed": 20, "wins": 13, "losses": 7, "winrate_pct": 65.0}, "recent_heroes": [{"hero_name": "Drow", "winrate_pct": 70.0, "is_smurf_hero": False}, {"hero_name": "Sniper", "winrate_pct": 60.0, "is_smurf_hero": False}], "smurf_verdict": {"class": "normal"}},
                {"name": "Ally_Mid", "rank_name": "Legend 5", "scouted": True, "recent_summary": {"matches_analyzed": 20, "wins": 11, "losses": 9, "winrate_pct": 55.0}, "recent_heroes": [{"hero_name": "Puck", "winrate_pct": 60.0, "is_smurf_hero": False}, {"hero_name": "Storm", "winrate_pct": 50.0, "is_smurf_hero": False}], "smurf_verdict": {"class": "normal"}},
                {"name": "Ally_Off", "rank_name": "Ancient 1", "scouted": True, "recent_summary": {"matches_analyzed": 20, "wins": 10, "losses": 10, "winrate_pct": 50.0}, "recent_heroes": [{"hero_name": "Axe", "winrate_pct": 50.0, "is_smurf_hero": False}, {"hero_name": "Centaur", "winrate_pct": 50.0, "is_smurf_hero": False}], "smurf_verdict": {"class": "normal"}},
                {"name": "Ally_Sup4", "rank_name": "Legend 4", "scouted": True, "recent_summary": {"matches_analyzed": 20, "wins": 12, "losses": 8, "winrate_pct": 60.0}, "recent_heroes": [{"hero_name": "Rubick", "winrate_pct": 65.0, "is_smurf_hero": False}, {"hero_name": "Mirana", "winrate_pct": 55.0, "is_smurf_hero": False}], "smurf_verdict": {"class": "normal"}},
                {"name": "Ally_Sup5", "rank_name": "Archon 5", "scouted": True, "recent_summary": {"matches_analyzed": 20, "wins": 9, "losses": 11, "winrate_pct": 45.0}, "recent_heroes": [{"hero_name": "Lion", "winrate_pct": 40.0, "is_smurf_hero": False}, {"hero_name": "WD", "winrate_pct": 50.0, "is_smurf_hero": False}], "smurf_verdict": {"class": "tilt"}},
            ]
            dire = [
                {"name": "EnemySmurf", "rank_name": "Ancient 1", "scouted": True, "recent_summary": {"matches_analyzed": 20, "wins": 17, "losses": 3, "winrate_pct": 85.0}, "recent_heroes": [{"hero_name": "Meepo", "winrate_pct": 85.0, "is_smurf_hero": True}, {"hero_name": "Tinker", "winrate_pct": 80.0, "is_smurf_hero": True}], "smurf_verdict": {"class": "danger"}},
                {"name": "Enemy_Carry", "rank_name": "Ancient 4", "scouted": True, "recent_summary": {"matches_analyzed": 20, "wins": 14, "losses": 6, "winrate_pct": 70.0}, "recent_heroes": [{"hero_name": "Slark", "winrate_pct": 75.0, "is_smurf_hero": False}, {"hero_name": "Jugg", "winrate_pct": 65.0, "is_smurf_hero": False}], "smurf_verdict": {"class": "warning"}},
                {"name": "Enemy_Off", "rank_name": "Ancient 2", "scouted": True, "recent_summary": {"matches_analyzed": 20, "wins": 10, "losses": 10, "winrate_pct": 50.0}, "recent_heroes": [{"hero_name": "Mars", "winrate_pct": 50.0, "is_smurf_hero": False}, {"hero_name": "Doom", "winrate_pct": 50.0, "is_smurf_hero": False}], "smurf_verdict": {"class": "normal"}},
                {"name": "Enemy_Sup4", "rank_name": "Legend 5", "scouted": True, "recent_summary": {"matches_analyzed": 20, "wins": 11, "losses": 9, "winrate_pct": 55.0}, "recent_heroes": [{"hero_name": "Tusk", "winrate_pct": 60.0, "is_smurf_hero": False}, {"hero_name": "Hoodwink", "winrate_pct": 50.0, "is_smurf_hero": False}], "smurf_verdict": {"class": "normal"}},
                {"name": "Enemy_Sup5", "rank_name": "Legend 2", "scouted": True, "recent_summary": {"matches_analyzed": 20, "wins": 7, "losses": 13, "winrate_pct": 35.0}, "recent_heroes": [{"hero_name": "CM", "winrate_pct": 35.0, "is_smurf_hero": False}, {"hero_name": "Disruptor", "winrate_pct": 30.0, "is_smurf_hero": False}], "smurf_verdict": {"class": "tilt"}},
            ]

        # Рассчитываем координаты под аватарками (16:9 widescreen стандарт)
        # 5 слотов слева (Radiant): ~8%..44% ширины экрана
        # 5 слотов справа (Dire): ~56%..92% ширины экрана
        # Y = 82px (аккурат под полоской героев вверху)
        card_w = min(112, int(self.sw * 0.058))
        card_h = 135
        y_pos = int(self.sh * 0.078)

        # Координаты X центров слотов в % от экрана
        rad_pcts = [0.110, 0.178, 0.246, 0.314, 0.382]
        dire_pcts = [0.618, 0.686, 0.754, 0.822, 0.890]

        # Отрисовка Radiant (Союзники)
        for i, p in enumerate(rad[:5]):
            x = int(self.sw * rad_pcts[i] - card_w // 2)
            card = self._create_player_card(p, team="radiant", x=x, y=y_pos, w=card_w, h=card_h)
            self.card_widgets.append(card)

        # Отрисовка Dire (Противники)
        for i, p in enumerate(dire[:5]):
            x = int(self.sw * dire_pcts[i] - card_w // 2)
            card = self._create_player_card(p, team="dire", x=x, y=y_pos, w=card_w, h=card_h)
            self.card_widgets.append(card)

        # Верхняя информационная плашка по центру (статус радара и смурфы)
        threats = lobby.get("threats_detected", 0)
        warns = lobby.get("warnings", [])
        if threats > 0 or warns:
            top_bar = tk.Frame(self.root, bg="#1a1423", bd=1, relief="solid", highlightbackground="#ef4444", highlightthickness=1)
            txt = f"🚨 ВНИМАНИЕ: Обнаружено угроз в лобби: {threats}!"
            if warns:
                txt += f" | {warns[0]}"
            lbl = tk.Label(top_bar, text=txt, bg="#1a1423", fg="#fca5a5", font=("Segoe UI", 9, "bold"), padx=10, pady=3)
            lbl.pack()
            tb_x = int(self.sw // 2 - 250)
            tb_y = int(y_pos + card_h + 10)
            top_bar.place(x=tb_x, y=tb_y, width=500, height=30)
            self.card_widgets.append(top_bar)

    def _create_player_card(self, p, team, x, y, w, h):
        """Создает стильную компактную плашку игрока под аватаркой."""
        v = p.get("smurf_verdict") or {}
        s = p.get("recent_summary") or {}
        is_scouted = p.get("scouted", False)

        # Цвета рамок
        accent = "#2dd4bf" if team == "radiant" else "#f43f5e"
        bg = "#11141c"
        if v.get("class") == "danger":
            bg = "#231114"
            accent = "#ef4444"
        elif v.get("class") == "warning":
            bg = "#211a12"
            accent = "#f59e0b"

        frame = tk.Frame(self.root, bg=bg, highlightbackground=accent, highlightthickness=1.5, bd=0)
        frame.place(x=x, y=y, width=w, height=h)

        # Ник + Ранг
        name = p.get("name") or f"Player {p.get('account_id', '')}"
        rank = p.get("rank_name") or "Unranked"
        name_lbl = tk.Label(frame, text=name[:12], bg=bg, fg="#ffffff", font=("Segoe UI", 8, "bold"), anchor="center")
        name_lbl.pack(fill="x", pady=(2, 0))

        rank_lbl = tk.Label(frame, text=rank[:14], bg=bg, fg="#94a3b8", font=("Segoe UI", 7), anchor="center")
        rank_lbl.pack(fill="x")

        # Винрейт
        if is_scouted and s.get("matches_analyzed"):
            wr = s.get("winrate_pct", 50)
            wr_color = "#34d399" if wr >= 60 else ("#f87171" if wr <= 40 else "#fbbf24")
            wr_txt = f"{wr}% ({s.get('wins', 0)}W-{s.get('losses', 0)}L)"
            wr_lbl = tk.Label(frame, text=wr_txt, bg=bg, fg=wr_color, font=("Segoe UI", 8, "bold"), anchor="center")
            wr_lbl.pack(fill="x", pady=(2, 0))

            # Топ 2-3 героя с винрейтом
            heroes = p.get("recent_heroes") or []
            hero_box = tk.Frame(frame, bg=bg)
            hero_box.pack(fill="both", expand=True, padx=2, pady=1)

            for h_info in heroes[:2]:
                h_name = h_info.get("hero_name", "")[:8]
                h_wr = h_info.get("winrate_pct", 50)
                fire = "🔥 " if h_info.get("is_smurf_hero") else ""
                h_color = "#34d399" if h_wr >= 60 else ("#f87171" if h_wr <= 40 else "#cbd5e1")
                h_lbl = tk.Label(hero_box, text=f"{fire}{h_name} {int(h_wr)}%", bg=bg, fg=h_color, font=("Segoe UI", 7), anchor="center")
                h_lbl.pack(fill="x")

            # Статус-бейдж
            b_text = "🚨 СМУРФ" if v.get("class") == "danger" else ("⚠️ ВИНСТРИК" if v.get("class") == "warning" else ("❄️ ТИЛЬТ" if v.get("class") == "tilt" else "🟢 НОРМА"))
            b_fg = "#ef4444" if v.get("class") == "danger" else ("#f59e0b" if v.get("class") == "warning" else ("#60a5fa" if v.get("class") == "tilt" else "#10b981"))
            status_lbl = tk.Label(frame, text=b_text, bg=bg, fg=b_fg, font=("Segoe UI", 7, "bold"), anchor="center")
            status_lbl.pack(side="bottom", fill="x", pady=2)
        else:
            wait_lbl = tk.Label(frame, text="⏳ Скан...", bg=bg, fg="#64748b", font=("Segoe UI", 8, "italic"), anchor="center")
            wait_lbl.pack(expand=True)

        return frame

    def run(self):
        self.root.mainloop()


def main():
    app = DraftOverlayApp()
    app.run()


if __name__ == "__main__":
    main()
