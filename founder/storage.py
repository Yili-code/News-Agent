import hashlib
import json
import sqlite3
import threading
from pathlib import Path


def _key(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class SQLiteStore:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        schema = Path(__file__).with_name("migrations").joinpath("0001.sql").read_text(encoding="utf-8")
        with self.lock:
            self.db.executescript(schema)

    def close(self):
        with self.lock:
            self.db.close()

    def valid_session(self, token_hash, timestamp):
        with self.lock:
            return self.db.execute(
                "SELECT 1 FROM sessions WHERE token=? AND expires>?", (token_hash, timestamp)
            ).fetchone() is not None

    def create_session(self, token_hash, expires, timestamp):
        with self.lock, self.db:
            self.db.execute("DELETE FROM sessions WHERE expires<?", (timestamp,))
            self.db.execute("INSERT INTO sessions(token,expires) VALUES(?,?)", (token_hash, expires))

    def revoke_session(self, token_hash):
        with self.lock, self.db:
            self.db.execute("DELETE FROM sessions WHERE token=?", (token_hash,))

    def record_login_attempt(self, ip, reset, timestamp):
        with self.lock, self.db:
            self.db.execute("DELETE FROM login_attempts WHERE reset<?", (timestamp,))
            row = self.db.execute("SELECT count,reset FROM login_attempts WHERE ip=?", (ip,)).fetchone()
            count = (row["count"] + 1) if row and row["reset"] >= timestamp else 1
            self.db.execute(
                "INSERT INTO login_attempts(ip,count,reset) VALUES(?,?,?) "
                "ON CONFLICT(ip) DO UPDATE SET count=excluded.count,reset=excluded.reset",
                (ip, count, reset),
            )
            return count

    def save_issue(self, issue, created):
        with self.lock, self.db:
            for signal in issue["signals"]:
                self.db.execute(
                    "INSERT INTO signals(id,body,topic,last_seen) VALUES(?,?,?,?) "
                    "ON CONFLICT(id) DO UPDATE SET body=excluded.body,topic=excluded.topic,last_seen=excluded.last_seen",
                    (signal["id"], json.dumps(signal, ensure_ascii=False), signal["topic"], issue["date"]),
                )
            self.db.execute(
                "INSERT OR IGNORE INTO issues(date,kind,body,created) VALUES(?,?,?,?)",
                (issue["date"], issue["kind"], json.dumps(issue, ensure_ascii=False), created),
            )

    def get_issue(self, date):
        with self.lock:
            row = self.db.execute("SELECT body FROM issues WHERE date=?", (date,)).fetchone()
            return json.loads(row["body"]) if row else None

    def context(self):
        with self.lock:
            issues = [json.loads(r["body"]) for r in self.db.execute("SELECT body FROM issues ORDER BY date DESC LIMIT 8")]
            feedback = [dict(r) for r in self.db.execute(
                "SELECT f.*,s.topic,s.body FROM feedback f JOIN signals s ON s.id=f.signal_id "
                "ORDER BY f.updated DESC LIMIT 200"
            )]
            return {"issues": issues, "feedback": feedback}

    def state(self):
        with self.lock:
            issues = [json.loads(r["body"]) for r in self.db.execute("SELECT body FROM issues ORDER BY date DESC LIMIT 90")]
            feedback = [dict(r) for r in self.db.execute(
                "SELECT f.*,s.body,s.topic FROM feedback f JOIN signals s ON s.id=f.signal_id ORDER BY f.updated DESC"
            )]
            deliveries = [dict(r) for r in self.db.execute("SELECT * FROM deliveries ORDER BY date DESC LIMIT 7")]
            return issues, feedback, deliveries

    def save_feedback(self, value, updated):
        with self.lock, self.db:
            if self.db.execute("SELECT 1 FROM signals WHERE id=?", (value["id"],)).fetchone() is None:
                return False
            self.db.execute(
                "INSERT INTO feedback(signal_id,reaction,saved,note,updated) VALUES(?,?,?,?,?) "
                "ON CONFLICT(signal_id) DO UPDATE SET reaction=excluded.reaction,saved=excluded.saved,note=excluded.note,updated=excluded.updated",
                (value["id"], value["reaction"], int(value["saved"]), value["note"], updated),
            )
            return True

    def claim_ai(self, day):
        with self.lock, self.db:
            row = self.db.execute("SELECT calls FROM ai_budget WHERE day=?", (day,)).fetchone()
            calls = row["calls"] if row else 0
            if calls >= 6:
                return False
            self.db.execute(
                "INSERT INTO ai_budget(day,calls) VALUES(?,1) ON CONFLICT(day) DO UPDATE SET calls=calls+1",
                (day,),
            )
            return True

    def claim_delivery(self, date, updated):
        with self.lock, self.db:
            try:
                self.db.execute("INSERT INTO deliveries(date,status,updated) VALUES(?,'sending',?)", (date, updated))
                return True
            except sqlite3.IntegrityError:
                return False

    def update_delivery(self, date, status, updated):
        with self.lock, self.db:
            self.db.execute("UPDATE deliveries SET status=?,updated=? WHERE date=?", (status, updated, date))

    def release_delivery(self, date):
        with self.lock, self.db:
            self.db.execute("DELETE FROM deliveries WHERE date=?", (date,))


class FirestoreStore:
    def __init__(self, project, database):
        from google.cloud import firestore

        self.firestore = firestore
        self.db = firestore.Client(project=project, database=database)

    def valid_session(self, token_hash, timestamp):
        data = self.db.collection("sessions").document(token_hash).get().to_dict()
        return bool(data and data.get("expires", 0) > timestamp)

    def create_session(self, token_hash, expires, timestamp):
        self.db.collection("sessions").document(token_hash).set({"expires": expires})

    def revoke_session(self, token_hash):
        self.db.collection("sessions").document(token_hash).delete()

    def record_login_attempt(self, ip, reset, timestamp):
        ref = self.db.collection("login_attempts").document(_key(ip))
        transaction = self.db.transaction()

        @self.firestore.transactional
        def update(tx):
            snapshot = ref.get(transaction=tx)
            data = snapshot.to_dict() or {}
            count = data.get("count", 0) + 1 if data.get("reset", 0) >= timestamp else 1
            tx.set(ref, {"count": count, "reset": reset})
            return count

        return update(transaction)

    def save_issue(self, issue, created):
        batch = self.db.batch()
        for signal in issue["signals"]:
            batch.set(
                self.db.collection("signals").document(_key(signal["id"])),
                {"id": signal["id"], "body": signal, "topic": signal["topic"], "last_seen": issue["date"]},
                merge=True,
            )
        issue_ref = self.db.collection("issues").document(issue["date"])
        if not issue_ref.get().exists:
            batch.set(issue_ref, {"date": issue["date"], "kind": issue["kind"], "body": issue, "created": created})
        batch.commit()

    def get_issue(self, date):
        data = self.db.collection("issues").document(date).get().to_dict()
        return data.get("body") if data else None

    def _feedback(self, limit=None):
        query = self.db.collection("feedback").order_by("updated", direction=self.firestore.Query.DESCENDING)
        if limit:
            query = query.limit(limit)
        rows = []
        for snapshot in query.stream():
            value = snapshot.to_dict()
            signal = self.db.collection("signals").document(_key(value["signal_id"])).get().to_dict() or {}
            rows.append({**value, "body": signal.get("body"), "topic": signal.get("topic")})
        return rows

    def context(self):
        issues = [s.to_dict()["body"] for s in self.db.collection("issues").order_by(
            "date", direction=self.firestore.Query.DESCENDING
        ).limit(8).stream()]
        return {"issues": issues, "feedback": self._feedback(200)}

    def state(self):
        issues = [s.to_dict()["body"] for s in self.db.collection("issues").order_by(
            "date", direction=self.firestore.Query.DESCENDING
        ).limit(90).stream()]
        deliveries = [s.to_dict() for s in self.db.collection("deliveries").order_by(
            "date", direction=self.firestore.Query.DESCENDING
        ).limit(7).stream()]
        return issues, self._feedback(), deliveries

    def save_feedback(self, value, updated):
        signal = self.db.collection("signals").document(_key(value["id"])).get()
        if not signal.exists:
            return False
        self.db.collection("feedback").document(_key(value["id"])).set(
            {"signal_id": value["id"], "reaction": value["reaction"], "saved": value["saved"], "note": value["note"], "updated": updated}
        )
        return True

    def claim_ai(self, day):
        ref = self.db.collection("ai_budget").document(day)
        transaction = self.db.transaction()

        @self.firestore.transactional
        def update(tx):
            snapshot = ref.get(transaction=tx)
            calls = (snapshot.to_dict() or {}).get("calls", 0)
            if calls >= 6:
                return False
            tx.set(ref, {"calls": calls + 1})
            return True

        return update(transaction)

    def claim_delivery(self, date, updated):
        ref = self.db.collection("deliveries").document(date)
        transaction = self.db.transaction()

        @self.firestore.transactional
        def claim(tx):
            if ref.get(transaction=tx).exists:
                return False
            tx.set(ref, {"date": date, "status": "sending", "updated": updated})
            return True

        return claim(transaction)

    def update_delivery(self, date, status, updated):
        self.db.collection("deliveries").document(date).set(
            {"date": date, "status": status, "updated": updated}, merge=True
        )

    def release_delivery(self, date):
        self.db.collection("deliveries").document(date).delete()
