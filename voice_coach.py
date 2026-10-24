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
        Evaluates current in-game clock time (seconds) and triggers timely audio cues.
        """
        if not is_in_game or clock_time < 0:
            return

        now = time.time()

        # 1. Wisdom Rune (Every 7 min = 420s: 7:00, 14:00, 21:00...)
        # Alert 20 sec before: at 400s, 820s, 1240s...
        if clock_time >= 400 and (clock_time % 420) == 400:
            if now - self.last_played_alert.get("wisdom", 0) > self.cooldown_sec:
                self.last_played_alert["wisdom"] = now
                self.play("wisdom_20s.mp3")
                return

        # 2. Bounty Runes (Every 3 min = 180s: 3:00, 6:00, 9:00...)
        # Alert 20 sec before: at 160s, 340s, 520s...
        if clock_time >= 160 and (clock_time % 180) == 160:
            if now - self.last_played_alert.get("bounty", 0) > self.cooldown_sec:
                self.last_played_alert["bounty"] = now
                self.play("bounty_20s.mp3")
                return

        # 3. River Power Runes (Every 2 min starting from 6:00 = 360s: 6:00, 8:00, 10:00...)
        # Alert 15 sec before: at 345s, 465s, 585s...
        if clock_time >= 345 and (clock_time % 120) == 105:
            if now - self.last_played_alert.get("river", 0) > self.cooldown_sec:
                self.last_played_alert["river"] = now
                self.play("river_15s.mp3")
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
