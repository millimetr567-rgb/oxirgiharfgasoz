"""
7 soniyalik o'yin taymeri moduli.

Mustaqil oqimda (threading) ishlaydi:
- Har 0.1 yoki 1 soniyada progress haqida xabar beradi.
- Vaqt tugaganda (0 soniya) 'on_timeout' callbackini chaqiradi.
- Gemini API so'rovlariga mutlaqo bog'liq emas.
"""

import time
import threading
from typing import Callable, Optional
from config import TURN_TIME_LIMIT


class GameTimer:
    """7 soniyalik aniq ortga hisoblash taymeri."""

    def __init__(self, duration: int = TURN_TIME_LIMIT):
        self.duration = duration
        self._remaining: float = float(duration)
        self._is_running: bool = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.on_tick: Optional[Callable[[int], None]] = None
        self.on_timeout: Optional[Callable[[], None]] = None

    @property
    def remaining(self) -> int:
        return max(0, int(round(self._remaining)))

    @property
    def is_running(self) -> bool:
        return self._is_running

    def start(
        self,
        on_tick: Optional[Callable[[int], None]] = None,
        on_timeout: Optional[Callable[[], None]] = None,
        duration: Optional[int] = None,
    ):
        """Taymerni yangidan ishga tushirish."""
        self.stop()

        if duration is not None:
            self.duration = duration

        self._remaining = float(self.duration)
        self.on_tick = on_tick
        self.on_timeout = on_timeout
        self._stop_event.clear()
        self._is_running = True

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """Taymerni to'xtatish."""
        self._is_running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive() and self._thread != threading.current_thread():
            self._thread.join(timeout=0.2)
        self._thread = None

    def _run(self):
        """Taymerning ichki hisoblash davri."""
        start_time = time.monotonic()
        last_reported_sec = self.duration

        # Boshlang'ich qiymatni xabar qilish
        if self.on_tick:
            try:
                self.on_tick(last_reported_sec)
            except Exception:
                pass

        while not self._stop_event.is_set():
            time.sleep(0.05)
            if self._stop_event.is_set():
                break

            elapsed = time.monotonic() - start_time
            self._remaining = max(0.0, float(self.duration) - elapsed)
            current_sec = int(round(self._remaining))

            # Agar butun soniya o'zgargan bo'lsa
            if current_sec != last_reported_sec and current_sec >= 0:
                last_reported_sec = current_sec
                if self.on_tick:
                    try:
                        self.on_tick(current_sec)
                    except Exception:
                        pass

            # Vaqt tugadi
            if self._remaining <= 0.05:
                self._is_running = False
                if self.on_timeout:
                    try:
                        self.on_timeout()
                    except Exception:
                        pass
                break
