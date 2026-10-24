"""
Dota 2 Cute Voice Coach & In-Game Timer Assistant
Plays natural, friendly female voice cues for runes, objectives, and match events.
100% local, zero tokens, zero API cost.
"""

import os
import sys
import time
from pathlib import Path
from typing import Optional, Set

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
        self.triggered_events: Set[str] = set()
        self.last_played_alert = {}
        self.cooldown_sec = 6.0

    def play(self, filename: str) -> bool:
        """Plays an audio cue from audio_cute directory asynchronously (non-blocking)."""
        if not HAS_AUDIO:
            return False
        path = AUDIO_DIR / filename
        if not path.exists():
            return False
        try:
            audio.play_audio_async(str(path))
            return True
        except Exception:
            return False

    def reset_match(self):
        """Resets triggered events on new match start."""
        self.triggered_events.clear()
        self.last_played_alert.clear()

    def check_timers(self, clock_time: int, is_in_game: bool = True) -> Optional[str]:
        """
        Evaluates current in-game clock time (seconds) and triggers timely audio cues.
        Uses window-based thresholds to guarantee triggers NEVER miss on 2s polling loops.
        Returns the filename if triggered, else None.
        """
        if not is_in_game or clock_time < 0:
            return None

        c = int(clock_time)

        # 1. Руны воды (на 02:00 = 120s и 04:00 = 240s) — окно за 18..8 сек
        if 102 <= c <= 114 and "water_120" not in self.triggered_events:
            self.triggered_events.add("water_120")
            self.play("water_15s.mp3")
            return "water_15s.mp3"

        if 222 <= c <= 234 and "water_240" not in self.triggered_events:
            self.triggered_events.add("water_240")
            self.play("water_15s.mp3")
            return "water_15s.mp3"

        # 2. Баунти руны (каждые 4 мин = 240s: 04:00, 08:00, 12:00...) — окно за 24..10 сек
        t_bounty = ((c + 20) // 240) * 240
        if t_bounty >= 240:
            rem_bounty = t_bounty - c
            if 10 <= rem_bounty <= 24 and f"bounty_{t_bounty}" not in self.triggered_events:
                self.triggered_events.add(f"bounty_{t_bounty}")
                self.play("bounty_20s.mp3")
                return "bounty_20s.mp3"

        # 3. Активные руны реки (начиная с 06:00 = 360s, каждые 2 мин = 120s) — окно за 18..8 сек
        t_river = ((c + 15) // 120) * 120
        if t_river >= 360:
            rem_river = t_river - c
            if 8 <= rem_river <= 18 and f"river_{t_river}" not in self.triggered_events:
                self.triggered_events.add(f"river_{t_river}")
                self.play("river_15s.mp3")
                return "river_15s.mp3"

        # 4. Руны мудрости (каждые 7 мин = 420s: 07:00, 14:00, 21:00...) — окно за 24..10 сек
        t_wisdom = ((c + 20) // 420) * 420
        if t_wisdom >= 420:
            rem_wisdom = t_wisdom - c
            if 10 <= rem_wisdom <= 24 and f"wisdom_{t_wisdom}" not in self.triggered_events:
                self.triggered_events.add(f"wisdom_{t_wisdom}")
                self.play("wisdom_20s.mp3")
                return "wisdom_20s.mp3"

        # 5. Смена дня и ночи / Переход Рошана (каждые 5 мин = 300s: 05:00, 10:00, 15:00...) — окно за 24..10 сек
        t_rosh = ((c + 20) // 300) * 300
        if t_rosh >= 300:
            rem_rosh = t_rosh - c
            if 10 <= rem_rosh <= 24 and f"roshan_{t_rosh}" not in self.triggered_events:
                self.triggered_events.add(f"roshan_{t_rosh}")
                self.play("roshan_move_20s.mp3")
                return "roshan_move_20s.mp3"

        # 6. Терзатель (на 20:00 = 1200s) — окно за 35..10 сек
        if 1165 <= c <= 1190 and "tormentor_1200" not in self.triggered_events:
            self.triggered_events.add("tormentor_1200")
            self.play("tormentor_30s.mp3")
            return "tormentor_30s.mp3"

        # 7. Лотусы (каждые 3 мин = 180s: 03:00, 06:00, 09:00...) — окно за 18..8 сек
        t_lotus = ((c + 15) // 180) * 180
        if t_lotus >= 180:
            rem_lotus = t_lotus - c
            # Не перебиваем активные руны реки на 360s, 720s...
            if 8 <= rem_lotus <= 18 and (t_lotus % 120 != 0 or t_lotus < 360) and f"lotus_{t_lotus}" not in self.triggered_events:
                self.triggered_events.add(f"lotus_{t_lotus}")
                self.play("lotus_20s.mp3")
                return "lotus_20s.mp3"

        return None

    def on_match_found(self):
        self.play("match_found.mp3")

    def on_game_start(self):
        self.reset_match()
        self.play("game_start.mp3")

    def on_victory(self):
        self.play("victory.mp3")


# Global singleton instance
coach = CuteVoiceCoach()


if __name__ == "__main__":
    print("Testing Cute Voice Coach...")
    coach.on_game_start()
    time.sleep(2)
