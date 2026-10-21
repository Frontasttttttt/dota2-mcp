import io
import json
import subprocess
import sys

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

SRV = "C:\\AI\\dota2-mcp\\server.py"

def call(name, args=None, idx=1):
    msg = {"jsonrpc": "2.0", "id": idx, "method": "tools/call",
           "params": {"name": name, "arguments": args or {}}}
    p = subprocess.run([sys.executable, SRV], input=json.dumps(msg).encode("utf-8"),
                       capture_output=True, timeout=30, cwd="C:\\AI\\dota2-mcp")
    out = (p.stdout or b"").decode("utf-8", "replace")
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                r = json.loads(line)
                txt = r["result"]["content"][0]["text"]
                print("=== %s %s ===" % (name, args))
                print(txt[:600] + ("..." if len(txt) > 600 else ""))
                return
            except Exception as e:
                print(name, "PARSE FAIL:", e, line[:300])
                return
    print(name, "NO OUTPUT. stderr:", p.stderr[:500])

call("dota_coach_tip", {"hero": "pudge", "minute": 20}, 1)
call("dota_pick_advice", {"enemies": ["sniper", "riki"]}, 2)
call("dota_match_details", {"match_id": 9054902632}, 3)
call("dota_gsi_status", {}, 4)
call("dota_whoami", {}, 5)
