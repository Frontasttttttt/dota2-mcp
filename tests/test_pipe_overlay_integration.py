import json
import os
import sys
import threading
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

import pipe_server


def test_pipe_server_direct():
    print("1. Starting pipe server...")
    srv = pipe_server.start_pipe_server()
    time.sleep(0.2)

    received_lines = []

    def mock_csharp_client():
        time.sleep(0.1)
        pipe_path = r"\\.\pipe\DotaOverlayPipe"
        with open(pipe_path, "rb") as f:
            for _ in range(2):
                line = f.readline()
                if not line:
                    break
                received_lines.append(line.decode("utf-8").strip())

    t = threading.Thread(target=mock_csharp_client)
    t.start()
    time.sleep(0.2)

    # Broadcast test board
    sample_board = {
        "ok": True,
        "stage": "DOTA_GAMERULES_STATE_GAME_IN_PROGRESS",
        "clock": 125.0,
        "timers": {
            "river_fmt": "01:55",
            "river_sec": 115,
            "bounty_fmt": "03:55",
            "bounty_sec": 235,
            "lotus_fmt": "02:55",
            "lotus_sec": 175,
            "wisdom_fmt": "06:55",
            "wisdom_sec": 415,
            "roshan_fmt": "01:30",
            "is_day": True,
            "tormentor_fmt": "20:00",
        },
    }

    srv.broadcast(sample_board)
    sample_board["clock"] = 126.0
    srv.broadcast(sample_board)

    t.join(timeout=3.0)
    print(f"2. Mock client received {len(received_lines)} packets.")
    assert len(received_lines) == 2, f"Expected 2 lines, got {len(received_lines)}"
    
    first = json.loads(received_lines[0])
    assert first.get("stage") == "DOTA_GAMERULES_STATE_GAME_IN_PROGRESS"
    assert first.get("clock") == 125.0
    
    second = json.loads(received_lines[1])
    assert second.get("clock") == 126.0
    print("SUCCESS: Pipe server direct test passed!")


if __name__ == "__main__":
    test_pipe_server_direct()
