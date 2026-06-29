import math
import random
from datetime import datetime
from leetpath.config import MASTERY_THRESHOLD
from leetpath.database.queries import (
    get_active_topic,
    get_assignments_for_date,
    insert_assignments,
    get_all_solve_logs,
    get_assignments_for_topic,
    get_problems_per_day,
    get_user_meta,
    get_db_conn
)

def get_days_elapsed(started_date_str: str, today_str: str) -> int:
    """Calculate the 1-based days elapsed in a topic."""
    started_dt = datetime.strptime(started_date_str, "%Y-%m-%d")
    today_dt = datetime.strptime(today_str, "%Y-%m-%d")
    delta = today_dt - started_dt
    return max(1, delta.days + 1)

def generate_daily_assignments(today_str: str = None, force: bool = False) -> list[dict]:
    """
    Generate and save assignments for today if they don't already exist.
    Returns the list of assignments.
    """
    if not today_str:
        today_str = datetime.today().strftime("%Y-%m-%d")
        
    # Start date constraint (start fresh from tomorrow)
    start_date_str = get_user_meta("start_date")
    if start_date_str and today_str < start_date_str:
        return []
        
    # Check if any topic has status='pending_start' AND scheduled_start_date <= today
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM topics WHERE status = 'pending_start' LIMIT 1")
    pending_topic = cursor.fetchone()
    conn.close()
    
    if pending_topic:
        sched_date = pending_topic["scheduled_start_date"]
        if sched_date and sched_date <= today_str:
            from leetpath.database.queries import update_topic_status, set_user_meta
            update_topic_status(pending_topic["id"], status="active", started_date=today_str)
            conn = get_db_conn()
            cursor = conn.cursor()
            cursor.execute("UPDATE topics SET scheduled_start_date = NULL WHERE id = ?", (pending_topic["id"],))
            conn.commit()
            conn.close()
            set_user_meta("next_topic_start_date", "")
            set_user_meta("current_topic_id", str(pending_topic["id"]))
            
    active_topic = get_active_topic()
    if not active_topic:
        # No active topic, can't generate new assignments, but return existing ones if any
        return get_assignments_for_date(today_str)
        
    problems_per_day = get_problems_per_day()
    
    if not force:
        # Check if assignments already exist for today
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as cnt FROM assignments 
            WHERE assigned_date = ? AND status IN ('pending', 'solved')
        """, (today_str,))
        count = cursor.fetchone()["cnt"]
        conn.close()
        
        if count > 0:
            return get_assignments_for_date(today_str)
    else:
        # Delete existing pending assignments for today to replace them
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM assignments 
            WHERE assigned_date = ? AND status = 'pending'
        """, (today_str,))
        conn.commit()
        conn.close()

    # Get all solved URLs to exclude them
    solve_logs = get_all_solve_logs()
    solved_urls = {item["leetcode_url"].rstrip('/') for item in solve_logs}
    
    # Get all previously assigned URLs for this topic to avoid immediate repetition
    prev_assignments = get_assignments_for_topic(active_topic["id"])
    assigned_urls = {item["leetcode_url"].rstrip('/') for item in prev_assignments}
    
    from leetpath.roadmap.neetcode150 import NEETCODE_150
    topic_problems = NEETCODE_150.get(active_topic["name"], [])
    
    # Find problems that are NOT solved and NOT assigned
    candidates = []
    for p in topic_problems:
        p_url = p["leetcode_url"].rstrip('/')
        if p_url not in solved_urls and p_url not in assigned_urls:
            candidates.append(p)
            
    if not candidates:
        # No new problems to assign in this topic
        return get_assignments_for_date(today_str)
        
    # Assign the next 2 (problems_per_day) in sequence
    selected = candidates[:problems_per_day]
        
    assignments_to_insert = []
    for p in selected:
        assignments_to_insert.append({
            "title": p["title"],
            "leetcode_url": p["leetcode_url"],
            "difficulty": p["difficulty"],
            "topic_id": active_topic["id"],
            "assigned_date": today_str
        })
        
    insert_assignments(assignments_to_insert)
    
    # Return the newly generated assignments
    return get_assignments_for_date(today_str)

def refresh_assignments_for_new_topic(old_topic_id: int, new_topic_id: int, today_str: str = None):
    """
    When a new topic is activated:
    1. Mark all remaining pending assignments for today from old topic as 'skipped'
    2. Generate fresh assignments from the new topic for today
    """
    if not today_str:
        today_str = datetime.today().strftime("%Y-%m-%d")
        
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE assignments 
        SET status = 'skipped'
        WHERE assigned_date = ? AND status = 'pending' AND topic_id = ?
    """, (today_str, old_topic_id))
    conn.commit()
    conn.close()
    
    generate_daily_assignments(today_str, force=True)

def generate_revisit_assignments(topic_id: int, today_str: str) -> bool:
    """Generate revisit assignments for a completed/skipped topic."""
    from leetpath.database.queries import get_topic_by_id, get_solves_for_topic
    topic = get_topic_by_id(topic_id)
    if not topic:
        return False
        
    solves = get_solves_for_topic(topic_id)
    if not solves:
        return False
        
    # Pick up to 5 random solved problems to revisit
    count = min(5, len(solves))
    chosen = random.sample(solves, count)
            
    assignments_to_insert = []
    for s in chosen:
        assignments_to_insert.append({
            "title": s["title"],
            "leetcode_url": s["leetcode_url"],
            "difficulty": s["difficulty"],
            "topic_id": topic_id,
            "assigned_date": today_str,
            "is_revisit": 1
        })
        
    insert_assignments(assignments_to_insert)
    return True
