import sqlite3
from datetime import datetime
from leetpath.database.setup import get_connection
from leetpath.fetcher.leetcode import normalize_leetcode_url

def dict_factory(cursor, row):
    """Convert SQLite row to dictionary."""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def get_db_conn():
    """Get connection with Row factory set."""
    conn = get_connection()
    conn.row_factory = dict_factory
    return conn

def is_db_initialized():
    """Check if the DB is seeded and metadata is present."""
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM user_meta WHERE key = 'start_date'")
        row = cursor.fetchone()
        conn.close()
        return row is not None
    except Exception:
        return False

def get_user_meta(key: str) -> str | None:
    """Retrieve a value from user_meta by key."""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM user_meta WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else None

def set_user_meta(key: str, value: str):
    """Set or update a key in user_meta."""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO user_meta (key, value) VALUES (?, ?)
    """, (key, str(value)))
    conn.commit()
    conn.close()

def get_active_topic():
    """Get the currently active topic."""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM topics WHERE status = 'active' LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return row

def get_topic_by_id(topic_id: int):
    """Get a topic by its ID."""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM topics WHERE id = ?", (topic_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def get_topic_by_order(order_index: int):
    """Get a topic by its order_index."""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM topics WHERE order_index = ?", (order_index,))
    row = cursor.fetchone()
    conn.close()
    return row

def get_all_topics():
    """Retrieve all 16 topics sorted by order_index."""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM topics ORDER BY order_index ASC")
    rows = cursor.fetchall()
    conn.close()
    return rows

def update_topic_status(topic_id: int, status: str, started_date=None, completed_date=None, mastery_score=None):
    """Update status and date fields for a topic."""
    conn = get_db_conn()
    cursor = conn.cursor()
    
    # We construct the query dynamically based on non-None values to avoid overwriting existing dates
    updates = [("status", status)]
    if started_date is not None:
        updates.append(("started_date", started_date))
    if completed_date is not None:
        updates.append(("completed_date", completed_date))
    if mastery_score is not None:
        updates.append(("mastery_score", mastery_score))
        
    set_clause = ", ".join([f"{col} = ?" for col, _ in updates])
    params = [val for _, val in updates]
    params.append(topic_id)
    
    cursor.execute(f"UPDATE topics SET {set_clause} WHERE id = ?", params)
    conn.commit()
    conn.close()

def get_assignments_for_date(date_str: str):
    """Get all assignments for a specific YYYY-MM-DD date."""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM assignments WHERE assigned_date = ?", (date_str,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def insert_assignments(assignments_list):
    """Bulk insert assignments. Each element is a dict with title, leetcode_url, difficulty, topic_id, assigned_date."""
    conn = get_db_conn()
    cursor = conn.cursor()
    for item in assignments_list:
        normalized_url = normalize_leetcode_url(item["leetcode_url"])
        cursor.execute("""
        INSERT INTO assignments (title, leetcode_url, difficulty, topic_id, assigned_date, status)
        VALUES (?, ?, ?, ?, ?, 'pending')
        """, (item["title"], normalized_url, item["difficulty"], item["topic_id"], item["assigned_date"]))
    conn.commit()
    conn.close()

def delete_assignments_for_date(date_str: str):
    """Delete all assignments for a specific YYYY-MM-DD date."""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM assignments WHERE assigned_date = ?", (date_str,))
    conn.commit()
    conn.close()

def get_assignment_by_url(url: str, status_filter=None):
    """Find an assignment by URL, optionally filtering by status."""
    normalized_url = normalize_leetcode_url(url)
    conn = get_db_conn()
    cursor = conn.cursor()
    if status_filter:
        cursor.execute("SELECT * FROM assignments WHERE leetcode_url = ? AND status = ? LIMIT 1", (normalized_url, status_filter))
    else:
        cursor.execute("SELECT * FROM assignments WHERE leetcode_url = ? LIMIT 1", (normalized_url,))
    row = cursor.fetchone()
    conn.close()
    return row

def mark_assignment_solved(assignment_id: int):
    """Update status of assignment to solved."""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE assignments SET status = 'solved' WHERE id = ?", (assignment_id,))
    conn.commit()
    conn.close()

def get_solve_log_by_url(url: str):
    """Get solve log by URL to check for duplicates."""
    normalized_url = normalize_leetcode_url(url)
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM solve_log WHERE leetcode_url = ? LIMIT 1", (normalized_url,))
    row = cursor.fetchone()
    conn.close()
    return row

def insert_solve_log(assignment_id, title, url, topic_id, difficulty, solved_date, time_taken, local_path, approach_note, is_assigned):
    """Insert a solved problem into the log."""
    normalized_url = normalize_leetcode_url(url)
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO solve_log (assignment_id, title, leetcode_url, topic_id, difficulty, solved_date, time_taken_minutes, local_path, approach_note, is_assigned)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (assignment_id, title, normalized_url, topic_id, difficulty, solved_date, time_taken, local_path, approach_note, is_assigned))
    conn.commit()
    conn.close()

def get_pending_assignments():
    """Retrieve all pending assignments from all past dates (older than today's date)."""
    today_str = datetime.today().strftime('%Y-%m-%d')
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT a.*, t.name as topic_name 
    FROM assignments a
    JOIN topics t ON a.topic_id = t.id
    WHERE a.status = 'pending' AND a.assigned_date < ?
    ORDER BY a.assigned_date DESC, a.id ASC
    """, (today_str,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_solve_history(topic_slug: str = None, difficulty: str = None, limit: int = None):
    """Get solved problems log with optional filters."""
    conn = get_db_conn()
    cursor = conn.cursor()
    
    query = """
    SELECT s.*, t.name as topic_name 
    FROM solve_log s
    JOIN topics t ON s.topic_id = t.id
    """
    filters = []
    params = []
    
    # Check if filtering by topic_slug
    if topic_slug:
        # Match either name or substring case-insensitively
        filters.append("(t.name LIKE ? OR ? LIKE '%' || t.name || '%')")
        params.extend([f"%{topic_slug}%", topic_slug])
        
    if difficulty:
        filters.append("LOWER(s.difficulty) = LOWER(?)")
        params.append(difficulty)
        
    if filters:
        query += " WHERE " + " AND ".join(filters)
        
    query += " ORDER BY s.solved_date DESC, s.id DESC"
    
    if limit:
        query += " LIMIT ?"
        params.append(limit)
        
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_all_solve_logs():
    """Retrieve all solve logs."""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM solve_log")
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_assignments_for_topic(topic_id: int):
    """Get all assignments for a given topic."""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM assignments WHERE topic_id = ?", (topic_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_solves_for_topic(topic_id: int):
    """Get all solved problems logged for a given topic (assigned + bonus)."""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM solve_log WHERE topic_id = ?", (topic_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def update_topic_state(topic_id: int, status: str, started_date: str | None, completed_date: str | None, mastery_score: float | None = None):
    """Fully update a topic's status, dates, and optional mastery."""
    conn = get_db_conn()
    cursor = conn.cursor()
    if mastery_score is not None:
        cursor.execute("""
        UPDATE topics 
        SET status = ?, started_date = ?, completed_date = ?, mastery_score = ?
        WHERE id = ?
        """, (status, started_date, completed_date, mastery_score, topic_id))
    else:
        cursor.execute("""
        UPDATE topics 
        SET status = ?, started_date = ?, completed_date = ?
        WHERE id = ?
        """, (status, started_date, completed_date, topic_id))
    conn.commit()
    conn.close()

def get_problems_per_day() -> int:
    """Get problems per day limit from user_meta, default to 5."""
    val = get_user_meta("problems_per_day")
    if val:
        try:
            return int(val)
        except ValueError:
            pass
    return 5

def update_solve_log(log_id: int, time_taken: int, local_path: str, approach_note: str):
    """Update an existing solve log entry."""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE solve_log
    SET time_taken_minutes = ?, local_path = ?, approach_note = ?
    WHERE id = ?
    """, (time_taken, local_path, approach_note, log_id))
    conn.commit()
    conn.close()

def delete_solve_log(log_id: int):
    """Delete a solve log entry."""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM solve_log WHERE id = ?", (log_id,))
    conn.commit()
    conn.close()

def mark_assignment_pending(assignment_id: int):
    """Update status of assignment to pending."""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE assignments SET status = 'pending' WHERE id = ?", (assignment_id,))
    conn.commit()
    conn.close()

def update_assignment_status(assignment_id: int, status: str):
    """Update status of assignment (e.g. to solved or pending)."""
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE assignments SET status = ? WHERE id = ?", (status, assignment_id))
    conn.commit()
    conn.close()

def find_pending_assignment_today(title: str, url: str, date_str: str) -> dict | None:
    """Find a pending assignment for today matching by title (case-insensitive) or by slug in URL."""
    conn = get_db_conn()
    cursor = conn.cursor()
    
    # 1. Try matching by title
    cursor.execute("""
    SELECT * FROM assignments
    WHERE assigned_date = ? AND LOWER(title) = ? AND status = 'pending'
    LIMIT 1
    """, (date_str, title.strip().lower()))
    row = cursor.fetchone()
    
    if row:
        conn.close()
        return row
        
    # 2. Try matching by slug
    from leetpath.fetcher.leetcode import extract_slug_from_url
    slug = extract_slug_from_url(url)
    if slug:
        like_pattern = f"%{slug}%"
        cursor.execute("""
        SELECT * FROM assignments
        WHERE assigned_date = ? AND leetcode_url LIKE ? AND status = 'pending'
        LIMIT 1
        """, (date_str, like_pattern))
        row = cursor.fetchone()
        if row:
            conn.close()
            return row
            
    conn.close()
    return None
