from leetpath.database.setup import initialize_database
from leetpath.database.queries import get_db_conn, set_user_meta

def restore():
    initialize_database()
    conn = get_db_conn()
    cursor = conn.cursor()
    
    # Wipe tables for clean restore
    cursor.execute("DELETE FROM solve_log")
    cursor.execute("DELETE FROM assignments")
    cursor.execute("UPDATE topics SET status = 'locked', started_date = NULL, completed_date = NULL, mastery_score = 0.0, scheduled_start_date = NULL")
    
    # Activate Arrays (order 1) with 12 estimated days
    cursor.execute("""
        UPDATE topics 
        SET status = 'active', started_date = '2026-06-23', estimated_days = 12 
        WHERE order_index = 1
    """)
    conn.commit()
    
    # Define the 5 daily assignments you had
    assignments = [
        {"title": "Best Time to Buy and Sell Stock", "url": "https://leetcode.com/problems/best-time-to-buy-and-sell-stock/", "diff": "Easy", "status": "solved"},
        {"title": "Majority Element", "url": "https://leetcode.com/problems/majority-element/", "diff": "Easy", "status": "solved"},
        {"title": "Contains Duplicate", "url": "https://leetcode.com/problems/contains-duplicate/", "diff": "Easy", "status": "solved"},
        {"title": "Product of Array Except Self", "url": "https://leetcode.com/problems/product-of-array-except-self/", "diff": "Medium", "status": "solved"},
        {"title": "3Sum", "url": "https://leetcode.com/problems/3sum/", "diff": "Medium", "status": "pending"}
    ]
    
    # Insert assignments
    inserted_ids = []
    for a in assignments:
        cursor.execute("""
            INSERT INTO assignments (title, leetcode_url, difficulty, topic_id, assigned_date, status)
            VALUES (?, ?, ?, 1, '2026-06-23', ?)
        """, (a["title"], a["url"], a["diff"], a["status"]))
        inserted_ids.append(cursor.lastrowid)
    conn.commit()
    
    # Insert solve logs
    solves = [
        {"idx": 0, "time": 30, "note": "using greedy approach"},
        {"idx": 1, "time": 30, "note": "initially variable dictionary but find the optimal solution in boyer moore algorithm"},
        {"idx": 2, "time": 15, "note": "O(N) space and time complexity"},
        {"idx": 3, "time": 20, "note": "prefix and suffix product arrays"}
    ]
    
    for s in solves:
        a = assignments[s["idx"]]
        ass_id = inserted_ids[s["idx"]]
        cursor.execute("""
            INSERT INTO solve_log (assignment_id, title, leetcode_url, topic_id, difficulty, solved_date, time_taken_minutes, approach_note, is_assigned)
            VALUES (?, ?, ?, 1, ?, '2026-06-23', ?, ?, 1)
        """, (ass_id, a["title"], a["url"], a["diff"], s["time"], s["note"]))
    conn.commit()
    
    # Recalculate and update mastery in topics table
    # 4 solved / 60 total expected = 6.67%
    cursor.execute("UPDATE topics SET mastery_score = 6.67 WHERE id = 1")
    conn.commit()
    
    conn.close()
    
    # Set metadata
    set_user_meta("current_topic_id", "1")
    set_user_meta("start_date", "2026-06-23")
    set_user_meta("streak_last_solved_date", "2026-06-23")
    set_user_meta("current_streak", "1")
    set_user_meta("best_streak", "1")
    
    print("Database restored to Day 1, with 4 solved assignments.")

if __name__ == "__main__":
    restore()
