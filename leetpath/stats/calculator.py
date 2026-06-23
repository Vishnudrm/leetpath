from datetime import datetime, timedelta
from leetpath.database.queries import (
    get_user_meta,
    set_user_meta,
    get_all_solve_logs,
    get_assignments_for_topic,
    get_solves_for_topic
)

def update_and_get_streaks(today_str: str = None) -> tuple[int, int]:
    """
    Calculate current streak and best streak.
    Update best streak in user_meta if current streak exceeds it.
    """
    if not today_str:
        today_str = datetime.today().strftime("%Y-%m-%d")
        
    solve_logs = get_all_solve_logs()
    if not solve_logs:
        return 0, int(get_user_meta("best_streak") or 0)
        
    # Gather all unique solve dates
    solve_dates = set()
    for log in solve_logs:
        if log["solved_date"]:
            solve_dates.add(log["solved_date"])
            
    today_dt = datetime.strptime(today_str, "%Y-%m-%d").date()
    yesterday_dt = today_dt - timedelta(days=1)
    
    today_str_normalized = today_dt.strftime("%Y-%m-%d")
    yesterday_str_normalized = yesterday_dt.strftime("%Y-%m-%d")
    
    current_streak = 0
    
    if today_str_normalized in solve_dates:
        # Streak continues from today
        current_streak = 0
        check_date = today_dt
        while check_date.strftime("%Y-%m-%d") in solve_dates:
            current_streak += 1
            check_date -= timedelta(days=1)
    elif yesterday_str_normalized in solve_dates:
        # Streak continues from yesterday
        current_streak = 0
        check_date = yesterday_dt
        while check_date.strftime("%Y-%m-%d") in solve_dates:
            current_streak += 1
            check_date -= timedelta(days=1)
    else:
        # Streak is broken
        current_streak = 0
        
    # Get and update best streak
    best_streak = int(get_user_meta("best_streak") or 0)
    if current_streak > best_streak:
        best_streak = current_streak
        set_user_meta("best_streak", str(best_streak))
        
    return current_streak, best_streak

def calculate_topic_mastery(topic_id: int) -> float:
    """
    Calculate mastery % for a topic:
    Mastery = problems solved in topic / total problems assigned for that topic so far.
    Capped at 100%.
    """
    assignments = get_assignments_for_topic(topic_id)
    assigned_count = len(assignments)
    if assigned_count == 0:
        return 0.0
        
    solves = get_solves_for_topic(topic_id)
    solved_count = len(solves)
    
    mastery = (solved_count / assigned_count) * 100.0
    return min(100.0, mastery)

def get_overall_stats_data(today_str: str = None) -> dict:
    """
    Compute overall stats:
    - Total solved count
    - Breakdown by difficulty (Easy, Medium, Hard)
    - Average solve time per difficulty
    - Total time spent
    - Streak stats
    - Days active since start
    - Most productive day
    - Breakdown by topic (sorted by solves desc)
    """
    if not today_str:
        today_str = datetime.today().strftime("%Y-%m-%d")
        
    solve_logs = get_all_solve_logs()
    total_solved = len(solve_logs)
    
    # Difficulty count and times
    diff_counts = {"Easy": 0, "Medium": 0, "Hard": 0}
    diff_times = {"Easy": [], "Medium": [], "Hard": []}
    
    total_time_spent = 0
    date_counts = {}
    topic_solve_counts = {}
    
    for log in solve_logs:
        diff = log["difficulty"].capitalize()
        if diff in diff_counts:
            diff_counts[diff] += 1
            
        time_taken = log["time_taken_minutes"]
        if time_taken is not None:
            total_time_spent += time_taken
            if diff in diff_times:
                diff_times[diff].append(time_taken)
                
        # Most productive day
        s_date = log["solved_date"]
        if s_date:
            date_counts[s_date] = date_counts.get(s_date, 0) + 1
            
        # Topic solves
        t_id = log["topic_id"]
        if t_id:
            topic_solve_counts[t_id] = topic_solve_counts.get(t_id, 0) + 1
            
    # Calculate averages
    avg_times = {}
    for diff, times in diff_times.items():
        if times:
            avg_times[diff] = sum(times) / len(times)
        else:
            avg_times[diff] = 0.0
            
    # Most productive day
    most_productive_day = "N/A"
    max_solves = 0
    for s_date, count in date_counts.items():
        if count > max_solves:
            max_solves = count
            most_productive_day = f"{s_date} ({count} solves)"
            
    # Streaks
    current_streak, best_streak = update_and_get_streaks(today_str)
    
    # Days active since start
    start_date_str = get_user_meta("start_date")
    days_active = 0
    if start_date_str:
        start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
        today_dt = datetime.strptime(today_str, "%Y-%m-%d")
        days_active = max(1, (today_dt - start_dt).days + 1)
        
    return {
        "total_solved": total_solved,
        "diff_counts": diff_counts,
        "avg_times": avg_times,
        "total_time_spent": total_time_spent,
        "current_streak": current_streak,
        "best_streak": best_streak,
        "days_active": days_active,
        "most_productive_day": most_productive_day,
        "topic_solve_counts": topic_solve_counts
    }
