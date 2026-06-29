import os
import sqlite3
from datetime import datetime
from leetpath.config import DB_DIR, DB_PATH, TOPIC_CONFIGS

def get_connection():
    """Create directory if not exists, and return a connection to SQLite."""
    os.makedirs(DB_DIR, exist_ok=True)
    return sqlite3.connect(DB_PATH)

def create_tables(conn):
    """Create schema tables if they do not exist."""
    cursor = conn.cursor()
    
    # 1. user_meta
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_meta (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)
    
    # 2. topics
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS topics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        order_index INTEGER NOT NULL,
        estimated_days INTEGER NOT NULL,
        track INTEGER NOT NULL,
        status TEXT DEFAULT 'locked',
        mastery_score REAL DEFAULT 0.0,
        started_date TEXT,
        completed_date TEXT,
        leetcode_slug TEXT,
        scheduled_start_date TEXT
    )
    """)
    
    # 3. assignments
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        leetcode_url TEXT NOT NULL,
        difficulty TEXT NOT NULL,
        topic_id INTEGER REFERENCES topics(id),
        assigned_date TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        is_revisit INTEGER DEFAULT 0
    )
    """)
    
    # 4. solve_log
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS solve_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        assignment_id INTEGER REFERENCES assignments(id),
        title TEXT NOT NULL,
        leetcode_url TEXT NOT NULL,
        topic_id INTEGER REFERENCES topics(id),
        difficulty TEXT NOT NULL,
        solved_date TEXT NOT NULL,
        time_taken_minutes INTEGER,
        local_path TEXT,
        approach_note TEXT,
        is_assigned INTEGER DEFAULT 1
    )
    """)
    
    # Upgrade existing database if leetcode_slug column doesn't exist
    try:
        cursor.execute("SELECT leetcode_slug FROM topics LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE topics ADD COLUMN leetcode_slug TEXT")
        # Update default topics
        for cfg in TOPIC_CONFIGS:
            cursor.execute("UPDATE topics SET leetcode_slug = ? WHERE name = ?", (cfg["slug"], cfg["name"]))
            
    # Upgrade existing database for is_revisit and scheduled_start_date
    try:
        cursor.execute("SELECT is_revisit FROM assignments LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE assignments ADD COLUMN is_revisit INTEGER DEFAULT 0")
        
    try:
        cursor.execute("SELECT scheduled_start_date FROM topics LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE topics ADD COLUMN scheduled_start_date TEXT")
        
    conn.commit()

def seed_topics(conn, start_date_str=None, topics_list=None):
    """Seed the topics into the topics table. Mark the starting topic as active."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM topics")
    if cursor.fetchone()[0] > 0:
        return  # Already seeded
    
    if not start_date_str:
        start_date_str = datetime.today().strftime('%Y-%m-%d')
        
    if not topics_list:
        topics_list = []
        for idx, cfg in enumerate(TOPIC_CONFIGS, start=1):
            topics_list.append({
                "name": cfg["name"],
                "estimated_days": cfg["days"],
                "track": cfg["track"],
                "leetcode_slug": cfg["slug"],
                "status": "active" if idx == 1 else "locked",
                "started_date": start_date_str if idx == 1 else None
            })
            
    for idx, item in enumerate(topics_list, start=1):
        cursor.execute("""
        INSERT INTO topics (name, order_index, estimated_days, track, status, mastery_score, started_date, completed_date, leetcode_slug)
        VALUES (?, ?, ?, ?, ?, 0.0, ?, NULL, ?)
        """, (item["name"], idx, item["estimated_days"], item["track"], item["status"], item["started_date"], item.get("leetcode_slug")))
        
    conn.commit()

def initialize_database(start_date_str=None, topics_list=None, problems_per_day=2):
    """Initialize schema and seed metadata / topics."""
    if not start_date_str:
        start_date_str = datetime.today().strftime('%Y-%m-%d')
        
    conn = get_connection()
    try:
        create_tables(conn)
        seed_topics(conn, start_date_str, topics_list)
        
        # Seed initial user meta
        cursor = conn.cursor()
        
        # Check if already present
        cursor.execute("SELECT COUNT(*) FROM user_meta")
        if cursor.fetchone()[0] == 0:
            active_index = 1
            if topics_list:
                for idx, t in enumerate(topics_list, start=1):
                    if t["status"] == "active":
                        active_index = idx
                        break
            
            cursor.executemany("""
            INSERT OR REPLACE INTO user_meta (key, value) VALUES (?, ?)
            """, [
                ("start_date", start_date_str),
                ("best_streak", "0"),
                ("current_topic_id", str(active_index)),
                ("problems_per_day", str(problems_per_day))
            ])
            conn.commit()
    finally:
        conn.close()

def reset_database():
    """Wipe the database completely."""
    import sqlite3
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM solve_log;")
        cursor.execute("DELETE FROM assignments;")
        cursor.execute("DELETE FROM topics;")
        cursor.execute("DELETE FROM user_meta;")
        conn.commit()
        
        # Verify counts are 0
        # When conn uses dict_factory, we can access by key or index since cursor fetchone doesn't use dict_factory (wait, does connection use it? get_connection() does NOT have dict_factory set!)
        # Let's check get_connection() in setup.py: it returns a raw sqlite3 connection without dict_factory. But we can alias it anyway just to be safe.
        for table in ["solve_log", "assignments", "topics", "user_meta"]:
            cursor.execute(f"SELECT COUNT(*) as cnt FROM {table}")
            cnt = cursor.fetchone()[0]
            assert cnt == 0, f"Table {table} still has {cnt} rows after reset"
    except sqlite3.OperationalError:
        pass
    finally:
        conn.close()
        
    try:
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
    except Exception:
        pass
