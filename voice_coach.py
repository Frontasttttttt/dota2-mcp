"""
Dota 2 Cute Voice Coach & In-Game Timer Assistant
Plays natural, friendly female voice cues for runes, objectives, and match events.
100% local, zero tokens, zero API cost.
"""

import os
import sys
import time
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent
AUDIO_DIR = BASE_DIR / "audio_cute"

# Add desktop-control for audio player
sys.path.insert(0, r"c:\AI\desktop-control")
try:
    import audio
    HAS_AUDIO = True
except Exception:
    HAS_AUDIO = False


class CuteVoiceCoach:
    def __init__(self):
        self.last_played_alert: Dict[str, float] = {}
        self.cooldown_sec = 15.0

    def play(self, filename: str) -> bool:
        """Plays an audio cue from audio_cute directory."""
        if not HAS_AUDIO:
            return False
        path = AUDIO_DIR / filename
        if not path.exists():
            return False
        return audio.play_audio(str(path))

    def check_timers(self, clock_time: int, is_in_game: bool = True):
        """
        Evaluates current in-game clock time (seconds) and triggers timely audio cues:
        - 1. Water runes: 02:00 (120s) and 04:00 (240s) -> alert 15s before (at 105s, 225s)
        - 2. River power runes: every 2m from 06:00 (360s) -> alert 15s before (at 345s, 465s, 585s...)
        - 3. Bounty runes: every 4m (240s) -> alert 20s before (at 220s, 460s, 700s...)
        - 4. Wisdom runes: every 7m (420s) -> alert 20s before (at 400s, 820s, 1240s...)
        - 5. Day/Night & Roshan relocation: every 5m (300s) -> alert 20s before (at 280s, 580s, 880s...)
        - 6. Tormentor spawn: at 20:00 (1200s) -> alert 30s before (at 1170s)
        - 7. Lotus pools: every 3m (180s) -> alert 15s before (at 165s, 525s...)
        """
        if not is_in_game or clock_time < 0:
            return

        now = time.time()

        # 1. Руны воды (на 02:00 = 120s и 04:00 = 240s) — за 15 сек (105s, 225s)
        if clock_time in (105, 225):
            if now - self.last_played_alert.get("water", 0) > self.cooldown_sec:
                self.last_played_alert["water"] = now
                self.play("water_15s.mp3")
                return

        # 2. Активные руны реки (начиная с 06:00 = 360s, каждые 2 мин = 120s) — за 15 сек (345s, 465s, 585s...)
        if clock_time >= 345 and (clock_time % 120) == 105:
            if now - self.last_played_alert.get("river", 0) > self.cooldown_sec:
                self.last_played_alert["river"] = now
                self.play("river_15s.mp3")
                return

        # 3. Баунти руны (каждые 4 мин = 240s: 04:00, 08:00, 12:00...) — за 20 сек (220s, 460s, 700s...)
        if clock_time >= 220 and (clock_time % 240) == 220:
            if now - self.last_played_alert.get("bounty", 0) > self.cooldown_sec:
                self.last_played_alert["bounty"] = now
                self.play("bounty_20s.mp3")
                return

        # 4. Руны мудрости (каждые 7 мин = 420s: 07:00, 14:00, 21:00...) — за 20 сек (400s, 820s, 1240s...)
        if clock_time >= 400 and (clock_time % 420) == 400:
            if now - self.last_played_alert.get("wisdom", 0) > self.cooldown_sec:
                self.last_played_alert["wisdom"] = now
                self.play("wisdom_20s.mp3")
                return

        # 5. Смена дня и ночи / Переход Рошана (каждые 5 мин = 300s: 05:00, 10:00, 15:00...) — за 20 сек (280s, 580s...)
        if clock_time >= 280 and (clock_time % 300) == 280:
            if now - self.last_played_alert.get("roshan_move", 0) > self.cooldown_sec:
                self.last_played_alert["roshan_move"] = now
                self.play("roshan_move_20s.mp3")
                return

        # 6. Терзатель (на 20:00 = 1200s) — за 30 сек (1170s)
        if clock_time == 1170:
            if now - self.last_played_alert.get("tormentor", 0) > self.cooldown_sec:
                self.last_played_alert["tormentor"] = now
                self.play("tormentor_30s.mp3")
                return

        # 7. Лотусы (каждые 3 мин = 180s: 03:00, 06:00, 09:00...) — за 15 сек (165s, 525s...)
        if clock_time >= 165 and (clock_time % 180) == 165 and (clock_time % 120) != 105:
            if now - self.last_played_alert.get("lotus", 0) > self.cooldown_sec:
                self.last_played_alert["lotus"] = now
                self.play("lotus_20s.mp3")
                return

    def on_match_found(self):
        self.play("match_found.mp3")

    def on_game_start(self):
        self.play("game_start.mp3")

    def on_victory(self):
        self.play("victory.mp3")


# Global singleton instance
coach = CuteVoiceCoach()


if __name__ == "__main__":
    print("Testing Cute Voice Coach...")
    coach.on_game_start()
    time.sleep(2)
