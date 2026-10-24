import os
import sys
import traceback

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

try:
    import watcher
    watcher.main()
except Exception as e:
    with open(os.path.join(BASE_DIR, "crash.log"), "w", encoding="utf-8") as f:
        f.write(traceback.format_exc())
