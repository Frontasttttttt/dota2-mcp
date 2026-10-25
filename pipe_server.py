"""pipe_server.py — Высокоскоростной Win32 Named Pipe сервер для передачи состояния в DotaOverlay.Wpf.

Zero-overhead, субмиллисекундная передача (<1 мс), без сетевых сокетов и HTTP-поллинга.
"""

import json
import logging
import threading
import time

try:
    import pywintypes
    import win32file
    import win32pipe

    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

logger = logging.getLogger("dota_pipe_server")

PIPE_NAME = r"\\.\pipe\DotaOverlayPipe"


class DotaPipeServer:
    def __init__(self, pipe_name: str = PIPE_NAME):
        self.pipe_name = pipe_name
        self.handle = None
        self._lock = threading.Lock()
        self._connected = False
        self._running = False
        self._latest_payload = None
        self._worker_thread = None

    def start(self):
        if not HAS_WIN32 or self._running:
            return
        self._running = True
        self._worker_thread = threading.Thread(
            target=self._server_loop, daemon=True, name="DotaPipeServerThread"
        )
        self._worker_thread.start()

    def _server_loop(self):
        while self._running:
            try:
                self.handle = win32pipe.CreateNamedPipe(
                    self.pipe_name,
                    win32pipe.PIPE_ACCESS_OUTBOUND,
                    win32pipe.PIPE_TYPE_BYTE | win32pipe.PIPE_WAIT,
                    win32pipe.PIPE_UNLIMITED_INSTANCES,
                    65536,
                    65536,
                    0,
                    None,
                )
                # Блокирующее ожидание подключения C# клиента
                win32pipe.ConnectNamedPipe(self.handle, None)
                with self._lock:
                    self._connected = True

                # При подключении сразу отправляем последнее актуальное состояние
                with self._lock:
                    payload = self._latest_payload
                if payload:
                    self._send_raw(payload)

                # Удерживаем соединение пока клиент подключен
                while self._running and self._connected:
                    time.sleep(0.05)

            except (pywintypes.error, OSError) as e:
                logger.debug("Pipe connection error: %s", e)
            finally:
                with self._lock:
                    self._connected = False
                    if self.handle:
                        try:
                            win32pipe.DisconnectNamedPipe(self.handle)
                        except (pywintypes.error, OSError) as e:
                            logger.debug("DisconnectNamedPipe error: %s", e)
                        try:
                            win32file.CloseHandle(self.handle)
                        except (pywintypes.error, OSError) as e:
                            logger.debug("CloseHandle error: %s", e)
                        self.handle = None
                time.sleep(0.1)

    def _send_raw(self, line_str: str) -> bool:
        if not self._connected or not self.handle:
            return False
        try:
            data = (line_str.strip() + "\n").encode("utf-8")
            win32file.WriteFile(self.handle, data)
            return True
        except (pywintypes.error, OSError) as e:
            logger.debug("WriteFile error: %s", e)
            with self._lock:
                self._connected = False
            return False

    def broadcast(self, data) -> bool:
        """Отправляет актуальное состояние (словарь или строка) клиенту оверлея."""
        if not HAS_WIN32:
            return False
        try:
            line = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
            with self._lock:
                self._latest_payload = line
            return self._send_raw(line)
        except (TypeError, ValueError) as e:
            logger.debug("JSON dump error: %s", e)
            return False

    def is_connected(self) -> bool:
        with self._lock:
            return self._connected

    def stop(self):
        self._running = False
        with self._lock:
            self._connected = False
            if self.handle:
                try:
                    win32file.CloseHandle(self.handle)
                except (pywintypes.error, OSError) as e:
                    logger.debug("Stop CloseHandle error: %s", e)
                self.handle = None


_instance = None
_instance_lock = threading.Lock()


def get_pipe_server() -> DotaPipeServer:
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = DotaPipeServer()
    return _instance


def start_pipe_server() -> DotaPipeServer:
    srv = get_pipe_server()
    srv.start()
    return srv


def broadcast_state(data) -> bool:
    srv = get_pipe_server()
    return srv.broadcast(data)
