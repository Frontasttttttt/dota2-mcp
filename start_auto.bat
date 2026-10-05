@echo off
chcp 65001 >nul
cd /d C:\AI\dota2-mcp
echo [1/3] GSI-приёмник...
start "dota2-gsi" /min python gsi_server.py
timeout /t 2 >nul
echo [2/3] Вотчер Dota 2...
start "dota2-watcher" /min python watcher.py
timeout /t 2 >nul
echo [3/3] Live-доска...
start "dota2-board" /min python live_board.py
echo Готово. Три окна свернуты: dota2-gsi, dota2-watcher, dota2-board.
echo Доска: http://127.0.0.1:8081
echo Логи: watcher_events.log
pause
