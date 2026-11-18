import sqlite3, json, hashlib, secrets, hmac
from pathlib import Path

DB_PATH = Path(__file__).with_name("careerforge.db")

def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def _hash_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 240000)
    return salt.hex(), digest.hex()

def init_db():
    with connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            salt TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            data_json TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )""")

def create_user(name, email, password):
    salt, digest = _hash_password(password)
    try:
        with connect() as conn:
            conn.execute("INSERT INTO users(name,email,salt,password_hash) VALUES(?,?,?,?)",
                         (name.strip(), email.strip().lower(), salt, digest))
        return True, "Account created successfully."
    except sqlite3.IntegrityError:
        return False, "An account with this email already exists."

def authenticate_user(email, password):
    with connect() as conn:
        row = conn.execute("SELECT id,name,email,salt,password_hash FROM users WHERE email=?",
                           (email.strip().lower(),)).fetchone()
    if not row:
        return None
    salt, digest = _hash_password(password, bytes.fromhex(row[3]))
    if hmac.compare_digest(digest, row[4]):
        return {"id": row[0], "name": row[1], "email": row[2]}
    return None

def save_resume(user_id, data):
    with connect() as conn:
        cur = conn.execute("INSERT INTO resumes(user_id,name,email,data_json) VALUES(?,?,?,?)",
                           (user_id, data.get("name",""), data.get("email",""),
                            json.dumps(data, ensure_ascii=False)))
        return cur.lastrowid

def list_resumes(user_id):
    with connect() as conn:
        return conn.execute("SELECT id,name,email,created_at FROM resumes WHERE user_id=? ORDER BY id DESC",
                            (user_id,)).fetchall()

def get_resume(user_id, resume_id):
    with connect() as conn:
        row = conn.execute("SELECT data_json FROM resumes WHERE user_id=? AND id=?",
                           (user_id, resume_id)).fetchone()
    return json.loads(row[0]) if row else None

def delete_resume(user_id, resume_id):
    with connect() as conn:
        conn.execute("DELETE FROM resumes WHERE user_id=? AND id=?", (user_id, resume_id))
