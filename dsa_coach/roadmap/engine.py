from datetime import datetime
from dsa_coach.database.queries import (
    get_active_topic,
    get_topic_by_order,
    get_all_topics,
    update_topic_status,
    set_user_meta,
    get_topic_by_id
)
from dsa_coach.stats.calculator import calculate_topic_mastery
from dsa_coach.assignments.generator import generate_daily_assignments

def is_track1_complete() -> bool:
    """Check if all Track 1 topics (order 1 to 10) are either complete or skipped."""
    topics = get_all_topics()
    track1_topics = [t for t in topics if t["track"] == 1]
    return all(t["status"] in ["complete", "skipped"] for t in track1_topics)

def get_roadmap_progress() -> tuple[float, float, bool]:
    """
    Calculate progress:
    - Track 1 completion %
    - Overall completion %
    - Placement Ready milestone (True/False)
    """
    topics = get_all_topics()
    
    track1_topics = [t for t in topics if t["track"] == 1]
    track1_done = sum(1 for t in track1_topics if t["status"] in ["complete", "skipped"])
    track1_pct = (track1_done / len(track1_topics)) * 100.0 if track1_topics else 0.0
    
    total_done = sum(1 for t in topics if t["status"] in ["complete", "skipped"])
    overall_pct = (total_done / len(topics)) * 100.0 if topics else 0.0
    
    # Placement Ready fires when all Track 1 is complete or skipped
    placement_ready = is_track1_complete()
    
    return track1_pct, overall_pct, placement_ready

def check_and_update_active_topic(today_str: str = None) -> bool:
    """
    Check if the active topic mastery has reached >= 70%.
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
    
    if mastery >= 70.0:
        update_topic_status(
            active["id"], 
            status="complete", 
            completed_date=today_str,
            mastery_score=mastery
        )
        return True
        
    return False

def advance_to_next_topic(today_str: str = None, force: bool = False) -> tuple[bool, str]:
    """
    Advance to the next sequential topic.
    If force is True, the current active topic status is marked as 'skipped' (if not already complete).
    Otherwise, if the active topic has mastery >= 70%, it is marked as 'complete'.
    Returns (success, message).
    """
    if not today_str:
        today_str = datetime.today().strftime("%Y-%m-%d")
        
    active = get_active_topic()
    if not active:
        # Check if there are any active topics. If not, maybe we can unlock the first locked one.
        # This could happen if the user finished everything or needs initialization.
        return False, "No active topic found. Run 'dsa start' to begin."
        
    mastery = calculate_topic_mastery(active["id"])
    
    # Determine new status for current topic
    if active["status"] == "active":
        if mastery >= 70.0:
            new_status = "complete"
        elif force:
            new_status = "skipped"
        else:
            return False, f"Current topic '{active['name']}' mastery is only {mastery:.1f}%. Solve more problems or use force to advance."
            
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
        return True, f"Congratulations! You have completed all {len(all_topics)} topics on the DSA Coach roadmap!"
        
    # Check Track 2 restriction
    if next_topic["track"] == 2 and not is_track1_complete():
        # If Track 2 is locked, we cannot advance yet.
        return False, "Track 2 is locked! Complete all Track 1 topics first."
        
    # Activate next topic
    update_topic_status(
        next_topic["id"],
        status="active",
        started_date=today_str
    )
    set_user_meta("current_topic_id", str(next_topic["id"]))
    
    # Generate fresh assignments for today for the new topic
    generate_daily_assignments(today_str)
    
    return True, f"Advanced to topic {next_topic['order_index']}: {next_topic['name']}. Fresh assignments generated!"

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
