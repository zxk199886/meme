"""SQLite persistence: rentals, action log, pool baseline."""
import sqlite3
import threading
import time

SCHEMA = """
CREATE TABLE IF NOT EXISTS rentals (
  id TEXT PRIMARY KEY, simulated INTEGER, label TEXT, gpu TEXT, num_gpus INTEGER,
  usd_per_hr REAL, started REAL, ended REAL, end_reason TEXT,
  cost REAL DEFAULT 0, prl_est REAL DEFAULT 0, last_accrued REAL);
CREATE TABLE IF NOT EXISTS events (ts REAL, kind TEXT, message TEXT, simulated INTEGER);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value REAL);
"""


class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        with self.lock:
            self.db.executescript(SCHEMA)

    def _exec(self, sql, args=()):
        with self.lock:
            cur = self.db.execute(sql, args)
            self.db.commit()
            return cur

    def _all(self, sql, args=()):
        with self.lock:
            return [dict(r) for r in self.db.execute(sql, args).fetchall()]

    def log(self, kind, message, simulated=False):
        self._exec("INSERT INTO events VALUES (?,?,?,?)", (time.time(), kind, message, int(simulated)))

    def events(self, limit=100):
        return self._all("SELECT * FROM events ORDER BY ts DESC LIMIT ?", (limit,))

    def open_rental(self, inst, simulated):
        start = inst.get("start_date") or time.time()
        self._exec("INSERT OR IGNORE INTO rentals (id, simulated, label, gpu, num_gpus, usd_per_hr, started, last_accrued)"
                   " VALUES (?,?,?,?,?,?,?,?)",
                   (str(inst["id"]), int(simulated), inst.get("label"), inst.get("gpu"), inst.get("num_gpus"),
                    inst.get("usd_per_hr"), start, start))

    def close_rental(self, rental_id, reason, now=None):
        self._exec("UPDATE rentals SET ended=?, end_reason=? WHERE id=? AND ended IS NULL",
                   (now or time.time(), reason, str(rental_id)))

    def open_rentals(self):
        return self._all("SELECT * FROM rentals WHERE ended IS NULL")

    def rentals(self, limit=200):
        return self._all("SELECT * FROM rentals ORDER BY started DESC LIMIT ?", (limit,))

    def accrue(self, rental_id, now, usd_per_hr, prl_per_sec):
        """Add cost and estimated PRL since the last accrual."""
        with self.lock:
            row = self.db.execute("SELECT last_accrued FROM rentals WHERE id=?", (str(rental_id),)).fetchone()
            if not row:
                return
            dt = max(0.0, now - (row["last_accrued"] or now))
            self.db.execute("UPDATE rentals SET cost=cost+?, prl_est=prl_est+?, usd_per_hr=?, last_accrued=? WHERE id=?",
                            (dt / 3600 * usd_per_hr, dt * prl_per_sec, usd_per_hr, now, str(rental_id)))
            self.db.commit()

    def totals(self, simulated):
        return self._all("SELECT COALESCE(SUM(cost),0) AS cost, COALESCE(SUM(prl_est),0) AS prl_est, COUNT(*) AS n"
                         " FROM rentals WHERE simulated=?", (int(simulated),))[0]

    def get_meta(self, key):
        rows = self._all("SELECT value FROM meta WHERE key=?", (key,))
        return rows[0]["value"] if rows else None

    def set_meta(self, key, value):
        self._exec("INSERT OR REPLACE INTO meta VALUES (?,?)", (key, value))
