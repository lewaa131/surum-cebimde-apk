"""Local midnight refresh, with retry after a suspended app or an open editor."""
from datetime import datetime, timedelta


class DayRefresh:
    def __init__(self, clock, refresh, blocked, now=datetime.now, on_error=None):
        self.clock, self.refresh, self.blocked, self.now = clock, refresh, blocked, now
        self.day = now().date()
        self.event = None
        self.on_error = on_error

    def check(self, *_):
        try:
            today = self.now().date()
            if today != self.day and not self.blocked():
                self.refresh()
                # Only acknowledge a successfully rendered day.
                self.day = today
        except Exception:
            if self.on_error is None: raise
            self.on_error()
        finally:
            self.schedule()

    def schedule(self):
        self.stop()
        now = self.now()
        midnight = datetime.combine(now.date() + timedelta(days=1), datetime.min.time())
        self.event = self.clock.schedule_once(self.check, max(.1, (midnight-now).total_seconds()+.1))

    def stop(self):
        if self.event is not None:
            self.event.cancel()
            self.event = None
