import sqlite3

conn = sqlite3.connect("casino.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users(
id INTEGER PRIMARY KEY,
balance REAL DEFAULT 100
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS settings(
key TEXT PRIMARY KEY,
value TEXT
)
""")

conn.commit()


def get_balance(user):

    cur.execute("SELECT balance FROM users WHERE id=?", (user,))
    row = cur.fetchone()

    if not row:
        cur.execute("INSERT INTO users(id,balance) VALUES(?,100)", (user,))
        conn.commit()
        return 100

    return row[0]


def set_balance(user, amount):

    cur.execute("UPDATE users SET balance=? WHERE id=?", (amount, user))
    conn.commit()


def change_balance(user, delta):

    balance = get_balance(user)
    balance += delta

    cur.execute("UPDATE users SET balance=? WHERE id=?", (balance, user))
    conn.commit()

    return balance


def get_setting(key):

    cur.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = cur.fetchone()

    if not row:
        return None

    return row[0]


def set_setting(key,value):

    cur.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)",(key,value))
    conn.commit()