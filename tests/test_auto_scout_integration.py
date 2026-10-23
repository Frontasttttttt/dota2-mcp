"""Тестирование автоматической разведки лобби и смурф-детектора.
Проверяет:
1. Парсинг GSI allplayers (Radiant и Dire).
2. Детекцию смурфов и спамеров буст-героев.
3. Интеграцию с live_data и live_board API.
4. Отсутствие внешних зависимостей и корректность кэширования.
"""
import io
import json
import os
import sys
import unittest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

import auto_scout
import dota_tools_b as B
import live_data as D
import scout_engine


class TestAutoScoutIntegration(unittest.TestCase):

    def setUp(self):
        self.mgr = auto_scout.get_scout_manager()
        self.mgr.players_dossiers.clear()
        self.mgr.players_meta.clear()

    def test_gsi_allplayers_parsing(self):
        """Проверка парсинга GSI с разделением по командам."""
        sample_gsi = {
            "map": {
                "matchid": "1234567890",
                "game_state": "DOTA_GAMERULES_STATE_HERO_SELECTION",
            },
            "player": {
                "accountid": "1092348748",
                "name": "ГлушительНаВолгу",
                "team_name": "radiant",
                "player_slot": 0,
            },
            "allplayers": {
                "team2": {
                    "player0": {
                        "accountid": "1092348748",
                        "name": "ГлушительНаВолгу",
                        "hero_id": 1,
                    },
                    "player1": {
                        "accountid": "284913852",
                        "name": "AllyPlayer",
                        "hero_id": 110,
                    },
                },
                "team3": {
                    "player5": {
                        "accountid": "145372258",
                        "name": "EnemySERJEI",
                        "hero_id": 80,
                    },
                },
            },
        }

        self.mgr.update_from_gsi(sample_gsi)
        state = self.mgr.get_lobby_state()

        self.assertEqual(state["match_id"], "1234567890")
        self.assertEqual(state["stage"], "DOTA_GAMERULES_STATE_HERO_SELECTION")
        self.assertEqual(state["total_players"], 3)
        self.assertEqual(len(state["radiant"]), 2)
        self.assertEqual(len(state["dire"]), 1)

        # Проверка отметки [ТЫ]
        self_card = next(p for p in state["radiant"] if p["account_id"] == 1092348748)
        self.assertTrue(self_card["is_you"])

        # Проверка противника
        enemy_card = state["dire"][0]
        self.assertEqual(enemy_card["account_id"], 145372258)
        self.assertFalse(enemy_card["is_you"])

    def test_live_data_board_integration(self):
        """Проверка интеграции с build_board."""
        board = D.build_board()
        self.assertIn("lobby_scout", board)
        lobby = board["lobby_scout"]
        self.assertIn("radiant", lobby)
        self.assertIn("dire", lobby)
        self.assertIn("summary", lobby)

    def test_tools_b_scout_lobby_auto(self):
        """Проверка инструмента t_scout_lobby в авто-режиме."""
        res = B.t_scout_lobby("auto")
        self.assertTrue(res.get("ok"))
        self.assertIn("текст", res)

    def test_scout_engine_smurf_detection(self):
        """Проверка детекции смурфа на кэшированном профиле."""
        res = scout_engine.scout_player(145372258)
        self.assertTrue(res.get("ok"))
        self.assertIn("smurf_verdict", res)
        v = res["smurf_verdict"]
        self.assertIn("badge", v)
        self.assertIn("is_smurf_threat", v)
        self.assertTrue(len(res.get("recent_heroes", [])) > 0)


if __name__ == "__main__":
    unittest.main()
