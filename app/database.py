"""
database.py — Thread-safe SQLite database layer.
Seeds user 'pankaj' on first init. Handles transactions and balance.
"""

import os
import sqlite3
import threading
import datetime
import uuid

DB_PATH = os.environ.get("DB_PATH", "/data/banking.db")
_lock = threading.Lock()


def _conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create schema and seed user 'pankaj' on first run."""
    with _lock:
        conn = _conn()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username    TEXT PRIMARY KEY,
                full_name   TEXT NOT NULL,
                account_no  TEXT NOT NULL,
                email       TEXT NOT NULL,
                tier        TEXT NOT NULL,
                balance     REAL NOT NULL DEFAULT 0.0,
                updated_at  TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                txn_id       TEXT PRIMARY KEY,
                username     TEXT NOT NULL,
                txn_type     TEXT NOT NULL,    -- CREDIT | DEBIT
                category     TEXT NOT NULL,
                description  TEXT NOT NULL,
                amount       REAL NOT NULL,
                balance_after REAL NOT NULL,
                cluster_name TEXT NOT NULL,
                status       TEXT NOT NULL DEFAULT 'COMMITTED',
                created_at   TEXT NOT NULL
            )
        """)

        # Seed pankaj once
        cur.execute("SELECT 1 FROM users WHERE username='pankaj'")
        if not cur.fetchone():
            now = _now()
            initial = 500000.00
            cur.execute("""
                INSERT INTO users (username, full_name, account_no, email, tier, balance, updated_at)
                VALUES (?,?,?,?,?,?,?)
            """, ("pankaj", "Pankaj Arora", "SB-8829-4100-PKJ",
                  "pankaj.arora@apexbank.in", "Priority Platinum", initial, now))

            cur.execute("""
                INSERT INTO transactions (txn_id,username,txn_type,category,description,
                    amount,balance_after,cluster_name,status,created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, ("TXN-SEED-0001", "pankaj", "CREDIT", "ACCOUNT_OPENING",
                  "Account Opening & KYC Funding",
                  initial, initial, os.environ.get("CLUSTER_NAME", "local"), "COMMITTED", now))

        conn.commit()
        conn.close()


def get_user(username="pankaj"):
    with _lock:
        conn = _conn()
        row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        conn.close()
        return dict(row) if row else None


def get_transactions(username="pankaj", limit=50):
    with _lock:
        conn = _conn()
        rows = conn.execute("""
            SELECT * FROM transactions WHERE username=?
            ORDER BY created_at DESC LIMIT ?
        """, (username, limit)).fetchall()
        conn.close()
        return [dict(r) for r in rows]


def post_transaction(username, txn_type, category, description, amount, cluster_name):
    """Atomically debit/credit and return the new transaction record."""
    with _lock:
        conn = _conn()
        cur = conn.cursor()

        row = cur.execute("SELECT balance FROM users WHERE username=?", (username,)).fetchone()
        if not row:
            conn.close()
            raise ValueError(f"User '{username}' not found")

        balance = row["balance"]
        txn_type = txn_type.upper()

        if txn_type == "CREDIT":
            new_balance = round(balance + amount, 2)
        elif txn_type == "DEBIT":
            if balance < amount:
                conn.close()
                raise ValueError("Insufficient balance")
            new_balance = round(balance - amount, 2)
        else:
            conn.close()
            raise ValueError(f"Invalid txn_type: {txn_type}")

        now = _now()
        txn_id = f"TXN-{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"

        cur.execute("UPDATE users SET balance=?, updated_at=? WHERE username=?",
                    (new_balance, now, username))
        cur.execute("""
            INSERT INTO transactions (txn_id,username,txn_type,category,description,
                amount,balance_after,cluster_name,status,created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (txn_id, username, txn_type, category, description,
              amount, new_balance, cluster_name, "COMMITTED", now))

        conn.commit()
        txn = dict(cur.execute("SELECT * FROM transactions WHERE txn_id=?", (txn_id,)).fetchone())
        conn.close()
        return txn


def reset(cluster_name):
    """Wipe all data and re-seed for demo replay."""
    with _lock:
        conn = _conn()
        conn.execute("DELETE FROM transactions")
        conn.execute("DELETE FROM users")
        conn.commit()
        conn.close()
    init_db()


def _now():
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
