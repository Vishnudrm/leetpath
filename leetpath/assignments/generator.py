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
    get_db_conn
)
from leetpath.fetcher.leetcode import fetch_problems_by_tag
from leetpath.fetcher.fallback import FALLBACK_PROBLEMS

def get_days_elapsed(started_date_str: str, today_str: str) -> int:
    """Calculate the 1-based days elapsed in a topic."""
    started_dt = datetime.strptime(started_date_str, "%Y-%m-%d")
    today_dt = datetime.strptime(today_str, "%Y-%m-%d")
    delta = today_dt - started_dt
    return max(1, delta.days + 1)

def get_difficulty_split(days_elapsed: int, estimated_days: int, problems_per_day: int) -> dict[str, int]:
    """
    Determine how many Easy, Medium, and Hard problems to assign.
    First half of topic:
      Easy slots = ceil(problems_per_day * 0.6)
      Medium slots = problems_per_day - easy_slots
    Second half of topic:
      Hard slots = ceil(problems_per_day * 0.4)
      Medium slots = ceil(problems_per_day * 0.4)
      Easy slots = problems_per_day - hard_slots - medium_slots
    """
    halfway = math.ceil(estimated_days / 2.0)
    if days_elapsed <= halfway:
        easy_slots = math.ceil(problems_per_day * 0.6)
        medium_slots = problems_per_day - easy_slots
        return {"Easy": easy_slots, "Medium": medium_slots, "Hard": 0}
    else:
        hard_slots = math.ceil(problems_per_day * 0.4)
        medium_slots = math.ceil(problems_per_day * 0.4)
        easy_slots = problems_per_day - hard_slots - medium_slots
        if easy_slots < 0:
            excess = -easy_slots
            reduce_med = min(excess, medium_slots)
            medium_slots -= reduce_med
            excess -= reduce_med
            if excess > 0:
                hard_slots -= excess
            easy_slots = 0
        return {"Easy": easy_slots, "Medium": medium_slots, "Hard": hard_slots}

def generate_daily_assignments(today_str: str = None, force: bool = False) -> list[dict]:
    """
    Generate and save assignments for today if they don't already exist.
    Returns the list of assignments.
    """
    if not today_str:
        today_str = datetime.today().strftime("%Y-%m-%d")
        
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
        
    started_date = active_topic["started_date"]
    if not started_date:
        started_date = today_str
        
    days_elapsed = get_days_elapsed(started_date, today_str)
    difficulty_split = get_difficulty_split(days_elapsed, active_topic["estimated_days"], problems_per_day)
    
    # Get all solved URLs to exclude them
    solve_logs = get_all_solve_logs()
    solved_urls = {item["leetcode_url"].rstrip('/') for item in solve_logs}
    
    # Get all previously assigned URLs for this topic to avoid immediate repetition
    prev_assignments = get_assignments_for_topic(active_topic["id"])
    assigned_urls = {item["leetcode_url"].rstrip('/') for item in prev_assignments}
    
    exclude_urls = solved_urls.union(assigned_urls)
    
    selected_problems = []
    
    # Resolve topic slug
    topic_slug = active_topic.get("leetcode_slug") or active_topic.get("slug")
    if not topic_slug:
        from leetpath.config import TOPIC_CONFIGS
        for cfg in TOPIC_CONFIGS:
            if cfg["name"].lower() == active_topic["name"].lower():
                topic_slug = cfg["slug"]
                break
    if not topic_slug:
        topic_slug = active_topic["name"].lower().replace(" ", "-")
        
    for diff, count in difficulty_split.items():
        if count == 0:
            continue
            
        problems_pool = []
        
        # 1. Try fetching from LeetCode GraphQL
        try:
            random_skip = random.randint(0, 40)
            fetched = fetch_problems_by_tag(topic_slug, diff, skip=random_skip, limit=20)
            
            if len(fetched) < count:
                fetched = fetch_problems_by_tag(topic_slug, diff, skip=0, limit=20)
                
            problems_pool = fetched
        except Exception:
            problems_pool = []
            
        # 2. Filter local fallback if GraphQL failed or returned nothing
        if not problems_pool:
            topic_fallback = FALLBACK_PROBLEMS.get(active_topic["name"], [])
            problems_pool = [
                p for p in topic_fallback 
                if p["difficulty"].lower() == diff.lower()
            ]
            
        # 3. Filter out excluded URLs
        unsolved_pool = [
            p for p in problems_pool 
            if p["leetcode_url"].rstrip('/') not in exclude_urls
        ]
        
        # 4. If we don't have enough unsolved problems, relax the restriction to avoid getting stuck
        if len(unsolved_pool) < count:
            unsolved_pool = [
                p for p in problems_pool 
                if p["leetcode_url"].rstrip('/') not in solved_urls
            ]
            
        if len(unsolved_pool) < count:
            unsolved_pool = problems_pool
            
        # 5. Randomly sample from the pool
        if len(unsolved_pool) >= count:
            chosen = random.sample(unsolved_pool, count)
        else:
            chosen = list(unsolved_pool)
            while len(chosen) < count and problems_pool:
                chosen.append(random.choice(problems_pool))
                
        selected_problems.extend(chosen)
        
    # Standardize to problems_per_day
    assignments_to_insert = []
    for p in selected_problems[:problems_per_day]:
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
    """Generate 5 revisit assignments for a completed/skipped topic."""
    from leetpath.database.queries import get_topic_by_id
    topic = get_topic_by_id(topic_id)
    if not topic:
        return False
        
    solve_logs = get_all_solve_logs()
    solved_urls = {item["leetcode_url"].rstrip('/') for item in solve_logs}
    
    prev_assignments = get_assignments_for_topic(topic_id)
    assigned_urls = {item["leetcode_url"].rstrip('/') for item in prev_assignments}
    
    exclude_urls = solved_urls.union(assigned_urls)
    
    topic_slug = topic.get("leetcode_slug") or topic.get("slug")
    if not topic_slug:
        topic_slug = topic["name"].lower().replace(" ", "-")
        
    # Get pool
    topic_fallback = FALLBACK_PROBLEMS.get(topic["name"], [])
    problems_pool = list(topic_fallback)
    
    try:
        for diff in ["Easy", "Medium", "Hard"]:
            fetched = fetch_problems_by_tag(topic_slug, diff, skip=0, limit=15)
            problems_pool.extend(fetched)
    except Exception:
        pass
        
    unique_pool = {}
    for p in problems_pool:
        url = p["leetcode_url"].rstrip('/')
        if url not in unique_pool:
            unique_pool[url] = p
            
    unsolved_pool = [
        p for url, p in unique_pool.items()
        if url not in exclude_urls
    ]
    
    if len(unsolved_pool) < 5:
        # Relax constraints: exclude solved, allow already assigned
        unsolved_pool = [
            p for url, p in unique_pool.items()
            if url not in solved_urls
        ]
        
    if len(unsolved_pool) < 5:
        unsolved_pool = list(unique_pool.values())
        
    if not unsolved_pool:
        return False
        
    if len(unsolved_pool) >= 5:
        chosen = random.sample(unsolved_pool, 5)
    else:
        chosen = list(unsolved_pool)
        all_vals = list(unique_pool.values())
        while len(chosen) < 5 and all_vals:
            chosen.append(random.choice(all_vals))
            
    assignments_to_insert = []
    for p in chosen[:5]:
        assignments_to_insert.append({
            "title": p["title"],
            "leetcode_url": p["leetcode_url"],
            "difficulty": p["difficulty"],
            "topic_id": topic_id,
            "assigned_date": today_str,
            "is_revisit": 1
        })
        
    insert_assignments(assignments_to_insert)
    return True
