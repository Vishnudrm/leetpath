from datetime import datetime
from leetpath.database.queries import (
    get_active_topic,
    get_topic_by_order,
    get_all_topics,
    update_topic_status,
    set_user_meta,
    get_topic_by_id
)
from leetpath.stats.calculator import calculate_topic_mastery
from leetpath.assignments.generator import generate_daily_assignments

def is_track1_complete() -> bool:
    """Check if all topics are either complete or skipped."""
    topics = get_all_topics()
    return all(t["status"] in ["complete", "skipped"] for t in topics)

def get_roadmap_progress() -> tuple[float, float, bool]:
    """
    Calculate progress:
    - Track 1 completion % (same as overall for NeetCode)
    - Overall completion %
    - Placement Ready milestone (True when all topics are complete or skipped)
    """
    topics = get_all_topics()
    total_done = sum(1 for t in topics if t["status"] in ["complete", "skipped"])
    overall_pct = (total_done / len(topics)) * 100.0 if topics else 0.0
    return overall_pct, overall_pct, total_done == len(topics)

def check_and_update_active_topic(today_str: str = None) -> bool:
    """
    Check if the active topic mastery has reached 100%.
    If so, update its status to 'complete' and return True.
    """
    if not today_str:
        today_str = datetime.today().strftime("%Y-%m-%d")
        
    active = get_active_topic()
    if not active or active["status"] != "active":
        return False
        
    mastery = calculate_topic_mastery(active["id"])
    
    # Update mastery score in topics table
    update_topic_status(active["id"], active["status"], mastery_score=mastery)
    
    if mastery >= 100.0:
        update_topic_status(
            active["id"], 
            status="complete", 
            completed_date=today_str,
            mastery_score=mastery
        )
        
        # Auto-advance to the next sequential topic
        next_order = active["order_index"] + 1
        next_topic = get_topic_by_order(next_order)
        
        if next_topic:
            from datetime import timedelta
            tomorrow_dt = datetime.strptime(today_str, "%Y-%m-%d") + timedelta(days=1)
            tomorrow_str = tomorrow_dt.strftime("%Y-%m-%d")
            
            from leetpath.database.queries import get_db_conn
            conn = get_db_conn()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE topics 
                SET status = 'pending_start', scheduled_start_date = ?
                WHERE id = ?
            """, (tomorrow_str, next_topic["id"]))
            conn.commit()
            conn.close()
            
            set_user_meta("next_topic_start_date", tomorrow_str)
            set_user_meta("current_topic_id", str(next_topic["id"]))
            
            # Print confirmation
            from rich.console import Console
            from rich.panel import Panel
            console = Console()
            confirmation_text = f"✓ {active['name']} complete!\n{next_topic['name']} starts tomorrow ({tomorrow_str}).\nRest today — you've earned it."
            console.print(Panel(confirmation_text, border_style="green"))
        return True
        
    return False

def advance_to_next_topic(today_str: str = None, force: bool = False) -> tuple[bool, str]:
    """
    Advance to the next sequential topic.
    The current active topic status is marked as 'complete' (or 'skipped' if forced and below threshold).
    The next topic is scheduled to start tomorrow with status='pending_start'.
    Returns (success, message).
    """
    if not today_str:
        today_str = datetime.today().strftime("%Y-%m-%d")
        
    active = get_active_topic()
    if not active:
        return False, "No active topic found. Run 'dsa start' to begin."
        
    mastery = calculate_topic_mastery(active["id"])
    
    # Determine new status for current topic
    if active["status"] == "active":
        if mastery >= 100.0:
            new_status = "complete"
        elif force:
            new_status = "skipped"
        else:
            return False, f"Current topic '{active['name']}' mastery is only {mastery:.1f}%. Solve all problems or use force to advance."
            
        update_topic_status(
            active["id"], 
            status=new_status, 
            completed_date=today_str,
            mastery_score=mastery
        )
    
    # Get next topic in order
    next_order = active["order_index"] + 1
    next_topic = get_topic_by_order(next_order)
    
    if not next_topic:
        all_topics = get_all_topics()
        return True, f"Congratulations! You have completed all {len(all_topics)} topics on the leetpath roadmap!"
        
    # Schedule next topic for tomorrow
    from datetime import timedelta
    tomorrow_dt = datetime.strptime(today_str, "%Y-%m-%d") + timedelta(days=1)
    tomorrow_str = tomorrow_dt.strftime("%Y-%m-%d")
    
    from leetpath.database.queries import get_db_conn
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE topics 
        SET status = 'pending_start', scheduled_start_date = ?
        WHERE id = ?
    """, (tomorrow_str, next_topic["id"]))
    conn.commit()
    conn.close()
    
    set_user_meta("next_topic_start_date", tomorrow_str)
    set_user_meta("current_topic_id", str(next_topic["id"]))
    
    return True, f"✓ {active['name']} complete!\n{next_topic['name']} starts tomorrow ({tomorrow_str}).\nRest today — you've earned it."

def resolve_topic_name(name: str, topics: list) -> dict | None:
    """
    Resolve a topic name or partial name from the list of topics.
    Handles case-insensitivity, partial matching, ambiguity resolution, and invalid name errors.
    Returns the resolved topic dict, or None if invalid.
    """
    from rich.console import Console
    from rich.prompt import Prompt
    console = Console()
    
    name_clean = name.strip().lower()
    if not name_clean:
        return None
        
    # 1. Exact match (case-insensitive)
    for t in topics:
        if t["name"].lower() == name_clean:
            return t
            
    # 2. Substring match (case-insensitive)
    candidates = []
    for t in topics:
        if name_clean in t["name"].lower():
            candidates.append(t)
            
    if len(candidates) == 1:
        return candidates[0]
        
    if len(candidates) > 1:
        console.print("[bold yellow]Ambiguous topic name. Did you mean one of these?[/bold yellow]")
        for i, cand in enumerate(candidates, 1):
            console.print(f"  [{i}] {cand['name']}")
        
        choice = Prompt.ask(
            "Select topic number",
            choices=[str(i) for i in range(1, len(candidates) + 1)],
            default="1"
        )
        return candidates[int(choice) - 1]
        
    # 3. No match found
    console.print(f"[bold red]Error: Invalid topic name '{name}'.[/bold red]")
    console.print("[bold cyan]Valid topic names are:[/bold cyan]")
    # Print topics organized nicely
    for t in topics:
        console.print(f"  - {t['name']}")
    return None
