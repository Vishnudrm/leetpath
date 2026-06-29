import typer
from datetime import datetime
from typing import Optional
from rich.prompt import Prompt, Confirm
from rich.console import Console

# Import configurations and db layers
from leetpath.config import MASTERY_THRESHOLD
from leetpath.database.setup import initialize_database, reset_database
from leetpath.database.queries import (
    is_db_initialized,
    get_user_meta,
    set_user_meta,
    get_active_topic,
    get_all_topics,
    get_assignments_for_date,
    get_assignment_by_url,
    get_solve_log_by_url,
    insert_solve_log,
    mark_assignment_solved,
    get_pending_assignments,
    get_solve_history,
    get_topic_by_id,
    get_solves_for_topic,
    get_assignments_for_topic,
    get_problems_per_day,
    update_solve_log,
    delete_solve_log,
    mark_assignment_pending,
    update_assignment_status,
    find_pending_assignment_today
)
from leetpath.assignments.generator import generate_daily_assignments
from leetpath.stats.calculator import (
    update_and_get_streaks,
    calculate_topic_mastery,
    get_overall_stats_data
)
from leetpath.roadmap.engine import (
    get_roadmap_progress,
    check_and_update_active_topic,
    advance_to_next_topic,
    resolve_topic_name
)
from leetpath.fetcher.leetcode import normalize_leetcode_url
from leetpath.dashboard.render import (
    render_welcome_screen,
    render_dashboard,
    render_today_assignments,
    render_roadmap,
    render_pending_assignments,
    render_progress,
    render_stats,
    render_history,
    render_topic_progress,
    get_difficulty_colored
)

app = typer.Typer(help="leetpath: Your terminal path through DSA — structured, tracked, placement-ready.")
console = Console()

def check_init():
    """Ensure database is initialized, otherwise instruct user and exit."""
    if not is_db_initialized():
        console.print("[bold red]Error: leetpath is not initialized yet.[/bold red]")
        console.print("Run [bold cyan]dsa start[/bold cyan] to initialize your study plan.\n")
        raise typer.Exit(code=1)

def show_dashboard(today_str: str):
    # 1. Check/generate assignments for today (ensure they exist)
    generate_daily_assignments(today_str)
    
    # 2. Check and update current active topic status (in case mastery crossed 70% in previous runs)
    check_and_update_active_topic(today_str)
    
    # 3. Retrieve active topic
    active_topic = get_active_topic()
    days_elapsed = 0
    if active_topic and active_topic["started_date"]:
        started_dt = datetime.strptime(active_topic["started_date"], "%Y-%m-%d")
        today_dt = datetime.strptime(today_str, "%Y-%m-%d")
        days_elapsed = max(1, (today_dt - started_dt).days + 1)
        
    # 4. Get today's assignment status
    from leetpath.dashboard.render import get_today_progress_stats
    today_solved, today_total = get_today_progress_stats(today_str)
    
    # 5. Get streaks
    current_streak, best_streak = update_and_get_streaks(today_str)
    
    # 6. Roadmap progress
    track1_pct, overall_pct, placement_ready = get_roadmap_progress()
    
    # 7. Day Number (overall preparation day)
    start_date_str = get_user_meta("start_date")
    day_num = 1
    if start_date_str:
        start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
        today_dt = datetime.strptime(today_str, "%Y-%m-%d")
        day_num = max(1, (today_dt - start_dt).days + 1)
        
    render_dashboard(
        day_num=day_num,
        today_date=today_str,
        active_topic=active_topic,
        days_elapsed=days_elapsed,
        today_solved=today_solved,
        today_total=today_total,
        current_streak=current_streak,
        best_streak=best_streak,
        track1_pct=track1_pct,
        overall_pct=overall_pct,
        placement_ready=placement_ready
    )

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Main callback to show the dashboard when dsa is run with no subcommand."""
    if ctx.invoked_subcommand is not None:
        return
        
    check_init()
    today_str = datetime.today().strftime("%Y-%m-%d")
    show_dashboard(today_str)

@app.command(name="start")
def start(
    topic: str = typer.Option("", "--topic", "-t", help="Start from a specific topic name")
):
    """Initialize NeetCode 150 study plan starting fresh from tomorrow."""
    today_str = datetime.today().strftime("%Y-%m-%d")
    from datetime import timedelta
    tomorrow_dt = datetime.today() + timedelta(days=1)
    tomorrow_str = tomorrow_dt.strftime("%Y-%m-%d")
    
    if is_db_initialized():
        confirm_wipe = Confirm.ask(
            "[bold yellow]leetpath has already been initialized. Wiping progress will permanently delete all logs. Continue?[/bold yellow]"
        )
        if not confirm_wipe:
            console.print("[cyan]Initialization aborted.[/cyan]\n")
            raise typer.Exit()
            
        console.print("[yellow]Wiping database...[/yellow]")
        reset_database()
        
    from leetpath.config import TOPIC_CONFIGS
    topics_list = []
    
    starting_idx = 0
    if topic:
        resolved = resolve_topic_name(topic, TOPIC_CONFIGS)
        if resolved:
            for idx, cfg in enumerate(TOPIC_CONFIGS):
                if cfg["name"].lower() == resolved["name"].lower():
                    starting_idx = idx
                    break
                    
    for idx, cfg in enumerate(TOPIC_CONFIGS):
        status = "locked"
        started_date = None
        if idx < starting_idx:
            status = "skipped"
        elif idx == starting_idx:
            status = "active"
            started_date = tomorrow_str
            
        topics_list.append({
            "name": cfg["name"],
            "estimated_days": cfg["days"],
            "track": cfg["track"],
            "leetcode_slug": cfg["slug"],
            "status": status,
            "started_date": started_date
        })
        
    problems_per_day = 2
    initialize_database(tomorrow_str, topics_list=topics_list, problems_per_day=problems_per_day)
    
    render_welcome_screen(tomorrow_str, problems_per_day=problems_per_day, total_topics=len(topics_list))

@app.command(name="today")
def today():
    """Display today's assigned problems."""
    check_init()
    today_str = datetime.today().strftime("%Y-%m-%d")
    
    # Ensure assignments exist
    assignments = generate_daily_assignments(today_str)
    render_today_assignments(assignments)

@app.command(name="roadmap")
def roadmap():
    """Display the NeetCode 150 roadmap of all 18 categories."""
    check_init()
    topics = get_all_topics()
    
    # Refresh mastery score for all topics (so the list shows updated scores)
    for t in topics:
        mastery = calculate_topic_mastery(t["id"])
        if t["status"] == "active" and mastery >= 100.0:
            from leetpath.database.queries import update_topic_status
            update_topic_status(t["id"], status="complete", completed_date=datetime.today().strftime("%Y-%m-%d"), mastery_score=mastery)
            t["status"] = "complete"
            t["mastery_score"] = mastery
        else:
            from leetpath.database.queries import update_topic_status
            update_topic_status(t["id"], status=t["status"], mastery_score=mastery)
            t["mastery_score"] = mastery
            
    # Reload topics for rendering
    topics = get_all_topics()
    _, overall_pct, _ = get_roadmap_progress()
    render_roadmap(topics, overall_pct)

@app.command(name="log")
def log(leetcode_url: Optional[str] = typer.Argument(None)):
    """Log a solved NeetCode 150 problem using its LeetCode URL."""
    check_init()
    today_str = datetime.today().strftime("%Y-%m-%d")
    
    # Step 1: Prompt for URL if not provided as argument
    if not leetcode_url:
        leetcode_url = typer.prompt("Enter LeetCode URL")
        
    # Normalize URL by removing spaces/slashes and subpaths
    leetcode_url = normalize_leetcode_url(leetcode_url)
    
    # Check if duplicate
    existing_solve = get_solve_log_by_url(leetcode_url)
    if existing_solve:
        console.print(f"[bold yellow]Warning: You have already logged this problem: '{existing_solve['title']}' on {existing_solve['solved_date']}.[/bold yellow]")
        console.print("Skipping to avoid duplicate logs.\n")
        raise typer.Exit()
        
    # Check if this URL is part of NeetCode 150
    from leetpath.roadmap.neetcode150 import NEETCODE_150
    from leetpath.fetcher.leetcode import extract_slug_from_url
    url_slug = extract_slug_from_url(leetcode_url)
    
    matched_nc_prob = None
    matched_nc_category = None
    for category, probs in NEETCODE_150.items():
        for p in probs:
            p_slug = extract_slug_from_url(p["leetcode_url"])
            if url_slug and p_slug and url_slug == p_slug:
                matched_nc_prob = p
                matched_nc_category = category
                break
        if matched_nc_prob:
            break
            
    if not matched_nc_prob:
        console.print(f"[bold red]Error: '{leetcode_url}' is not a NeetCode 150 problem.[/bold red]")
        console.print("[yellow]Only NeetCode 150 problems can be logged to maintain roadmap integrity.[/yellow]\n")
        raise typer.Exit(code=1)
        
    title = matched_nc_prob["title"]
    difficulty = matched_nc_prob["difficulty"].capitalize()
    
    console.print(f"Problem details: [bold cyan]{title}[/bold cyan] ({difficulty})")
    
    # Step 3: Confirm
    confirm_log = Confirm.ask("Confirm")
    if not confirm_log:
        console.print("[yellow]Log aborted.[/yellow]\n")
        raise typer.Exit()
        
    # Step 4: Local file path
    local_path = Prompt.ask("Local file path (optional, press Enter to skip)", default="")
    
    # Step 5: Time taken
    time_taken_str = Prompt.ask("Time taken (minutes)")
    try:
        time_taken = int(time_taken_str)
    except ValueError:
        console.print("[yellow]Invalid duration. Setting time taken to 0 minutes.[/yellow]")
        time_taken = 0
        
    # Step 6: Approach note
    approach_note = Prompt.ask("Approach note (optional, press Enter to skip)", default="")
    
    # Step 7: Save solve log and show confirmation
    # Look up the topic ID for matched_nc_category from the database
    from leetpath.database.queries import get_db_conn
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM topics WHERE name = ?", (matched_nc_category,))
    topic_row = cursor.fetchone()
    conn.close()
    
    if not topic_row:
        console.print(f"[bold red]Error: Topic '{matched_nc_category}' not found in database.[/bold red]")
        raise typer.Exit(code=1)
    topic_id = topic_row["id"]
    
    # Find matching assignment by comparing title or url against today's assignments
    matched_assignment = find_pending_assignment_today(title, leetcode_url, today_str)
    
    active_topic = get_active_topic()
    
    if matched_assignment:
        # Mark assignment solved
        update_assignment_status(matched_assignment["id"], 'solved')
        # Insert log linked to assignment
        insert_solve_log(
            assignment_id=matched_assignment["id"],
            title=title,
            url=leetcode_url,
            topic_id=topic_id,
            difficulty=difficulty,
            solved_date=today_str,
            time_taken=time_taken,
            local_path=local_path,
            approach_note=approach_note,
            is_assigned=1
        )
        console.print(f"[bold green]Successfully logged assignment: '{title}'![/bold green]")
        console.print("✓ Marked as solved in today's assignments.")
    else:
        # Log as bonus/unassigned solve under its category
        insert_solve_log(
            assignment_id=None,
            title=title,
            url=leetcode_url,
            topic_id=topic_id,
            difficulty=difficulty,
            solved_date=today_str,
            time_taken=time_taken,
            local_path=local_path,
            approach_note=approach_note,
            is_assigned=0
        )
        console.print(f"[bold green]Successfully logged solve: '{title}' under category '{matched_nc_category}'![/bold green]")
        
    # Always check/update the active topic completion
    if active_topic:
        check_and_update_active_topic(today_str)
        refreshed_active = get_topic_by_id(active_topic["id"])
        if refreshed_active and refreshed_active["status"] == "complete":
            console.print(
                f"\n[bold green]★ Topic threshold reached (100% mastery)! ★[/bold green]\n"
                "Run [bold cyan]dsa next[/bold cyan] to advance to the next topic!\n"
            )

@app.command(name="pending")
def pending():
    """Display pending assignments from past dates."""
    check_init()
    assignments = get_pending_assignments()
    render_pending_assignments(assignments)

@app.command(name="progress")
def progress():
    """Display per-topic detailed progress report."""
    check_init()
    topics = get_all_topics()
    
    # Update mastery scores before rendering
    for t in topics:
        mastery = calculate_topic_mastery(t["id"])
        # Update in DB
        from leetpath.database.queries import update_topic_status
        update_topic_status(t["id"], status=t["status"], mastery_score=mastery)
        t["mastery_score"] = mastery
        
    _, _, placement_ready = get_roadmap_progress()
    render_progress(topics, placement_ready)

@app.command(name="stats")
def stats():
    """Display overall preparation statistics."""
    check_init()
    today_str = datetime.today().strftime("%Y-%m-%d")
    stats_data = get_overall_stats_data(today_str)
    render_stats(stats_data)

@app.command(name="history")
def history(
    topic: str = typer.Option(None, help="Filter history by topic name or slug"),
    difficulty: str = typer.Option(None, help="Filter history by difficulty (Easy/Medium/Hard)"),
    last: int = typer.Option(None, help="Limit number of logs displayed")
):
    """Display solve history with optional filters."""
    check_init()
    history_logs = get_solve_history(topic_slug=topic, difficulty=difficulty, limit=last)
    render_history(history_logs)

@app.command(name="edit")
def edit():
    """Edit or delete a previously logged solve."""
    check_init()
    
    # Step 1 — Show recent solve history (last 10 entries) as a numbered list
    logs = get_solve_history(limit=10)
    if not logs:
        console.print("[yellow]No logged solves found.[/yellow]")
        raise typer.Exit()
        
    from rich.table import Table
    table = Table(title="[bold cyan]Recent Solve History[/bold cyan]", border_style="cyan")
    table.add_column("#", justify="center", width=4)
    table.add_column("Date", justify="center", width=12)
    table.add_column("Problem Name", justify="left")
    table.add_column("Difficulty", justify="center", width=12)
    table.add_column("Time", justify="center", width=10)
    
    for idx, log in enumerate(logs, start=1):
        time_str = f"{log['time_taken_minutes']} min" if log['time_taken_minutes'] else "-"
        table.add_row(
            str(idx),
            log["solved_date"],
            log["title"],
            get_difficulty_colored(log["difficulty"]),
            time_str
        )
    console.print(table)
    
    # Step 2 — Prompt
    while True:
        choice_str = Prompt.ask("Enter the # of the log to edit (or 0 to cancel)")
        try:
            choice = int(choice_str)
            if 0 <= choice <= len(logs):
                break
            else:
                console.print(f"[red]Please enter an integer between 0 and {len(logs)}.[/red]")
        except ValueError:
            console.print("[red]Please enter a valid integer.[/red]")
            
    if choice == 0:
        console.print("No changes made.")
        raise typer.Exit()
        
    selected_log = logs[choice - 1]
    
    # Step 3 — Show current values and prompt for new ones
    console.print(f"Problem: {selected_log['title']}")
    
    current_time = selected_log['time_taken_minutes']
    time_taken_str = Prompt.ask("Time taken", default=str(current_time) if current_time is not None else "0")
    try:
        time_taken = int(time_taken_str)
    except ValueError:
        time_taken = current_time or 0
        
    current_path = selected_log['local_path'] or ""
    local_path = Prompt.ask("Local file path", default=current_path)
    
    current_approach = selected_log['approach_note'] or ""
    approach_note = Prompt.ask("Approach note", default=current_approach)
    
    # Step 4 — Action menu
    console.print("\nWhat do you want to do?")
    console.print("  [1] Save changes")
    console.print("  [2] Delete this log entry")
    console.print("  [3] Cancel")
    
    action = Prompt.ask("Select an option", choices=["1", "2", "3"])
    
    # Step 5 — Save
    if action == "1":
        update_solve_log(selected_log["id"], time_taken, local_path, approach_note)
        console.print("✓ Log updated successfully.")
        
    # Step 6 — Delete
    elif action == "2":
        confirm_delete = Confirm.ask(
            f"Delete log for {selected_log['title']}? This will mark it as pending again.",
            default=False
        )
        if confirm_delete:
            delete_solve_log(selected_log["id"])
            if selected_log["is_assigned"] == 1 and selected_log["assignment_id"] is not None:
                mark_assignment_pending(selected_log["assignment_id"])
                
            # Recalculate topic mastery
            topic_id = selected_log["topic_id"]
            new_mastery = calculate_topic_mastery(topic_id)
            topic = get_topic_by_id(topic_id)
            if topic:
                from leetpath.database.queries import update_topic_status
                update_topic_status(topic_id, status=topic["status"], mastery_score=new_mastery)
                
            # Keep active topic status in sync
            today_str = datetime.today().strftime("%Y-%m-%d")
            check_and_update_active_topic(today_str)
            
            console.print("✓ Log deleted. Problem marked as pending.")
        else:
            console.print("No changes made.")
            
    # Step 7 — Cancel
    elif action == "3":
        console.print("No changes made.")
        raise typer.Exit()

@app.command(name="next")
def next_topic():
    """Advance to the next sequential topic."""
    check_init()
    today_str = datetime.today().strftime("%Y-%m-%d")
    
    active = get_active_topic()
    if not active:
        from leetpath.database.queries import get_db_conn
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM topics WHERE status = 'locked' ORDER BY order_index ASC LIMIT 1")
        next_locked = cursor.fetchone()
        conn.close()
        
        if next_locked:
            update_topic_status(next_locked["id"], status="active", started_date=today_str)
            set_user_meta("current_topic_id", str(next_locked["id"]))
            console.print(f"No active topic detected. Activating {next_locked['name']}...")
            generate_daily_assignments(today_str)
        else:
            console.print("[yellow]No locked topics remaining.[/yellow]")
        raise typer.Exit()
        
    mastery = calculate_topic_mastery(active["id"])
    
    # Warn user if mastery < 100%
    if mastery < 100.0:
        confirm = Confirm.ask(
            f"{active['name']} mastery: {mastery:.0f}% (below 100% threshold). Advance anyway?"
        )
        if not confirm:
            console.print("[cyan]Staying on active topic.[/cyan]\n")
            raise typer.Exit()
            
        success, msg = advance_to_next_topic(today_str, force=True)
    else:
        success, msg = advance_to_next_topic(today_str, force=False)
        
    if success:
        from rich.panel import Panel
        console.print(Panel(msg, border_style="green"))
    else:
        console.print(f"[bold red]Failed to advance: {msg}[/bold red]\n")

@app.command(name="reset")
def reset():
    """Wipe the database completely and restart."""
    confirm_reset = Confirm.ask(
        "[bold red]This will completely wipe your database, streak, and history. Are you absolutely sure?[/bold red]"
    )
    if not confirm_reset:
        console.print("[cyan]Reset aborted.[/cyan]\n")
        raise typer.Exit()
        
    reset_database()
    console.print("[bold green]Database has been reset successfully.[/bold green]")
    console.print("Run [bold cyan]dsa start[/bold cyan] to initialize again.\n")

@app.command(name="topic")
def topic_cmd(
    name: str = typer.Argument(..., help="The name or partial name of the topic"),
    action: str = typer.Argument("progress", help="The action to perform (default: progress)")
):
    """View detailed progress for a specific topic."""
    check_init()
    topics = get_all_topics()
    resolved = resolve_topic_name(name, topics)
    if not resolved:
        raise typer.Exit(code=1)
        
    if action.lower() == "progress":
        solves = get_solves_for_topic(resolved["id"])
        assignments = get_assignments_for_topic(resolved["id"])
        problems_per_day = get_problems_per_day()
        render_topic_progress(resolved, solves, assignments, problems_per_day)
    else:
        console.print(f"[red]Error: Unknown action '{action}'. Currently only 'progress' is supported.[/red]")
        raise typer.Exit(code=1)

@app.command(name="move")
def move_cmd(
    topic_name: str = typer.Argument(..., help="Target topic name or partial name")
):
    """Jump the active topic to any topic regardless of current position."""
    check_init()
    today_str = datetime.today().strftime("%Y-%m-%d")
    
    topics = get_all_topics()
    resolved = resolve_topic_name(topic_name, topics)
    if not resolved:
        raise typer.Exit(code=1)
        
    active = get_active_topic()
    active_id = active["id"] if active else None
    
    if active_id and resolved["id"] == active_id:
        console.print(f"Already on {resolved['name']}. No change made.\n")
        raise typer.Exit()
        
    console.print(f"Moving to {resolved['name']}. All topics before it will be marked skipped.")
    
    confirm = Confirm.ask("Confirm move?", default=False)
    if not confirm:
        console.print("[cyan]Move aborted.[/cyan]\n")
        raise typer.Exit()
        
    # Update topics
    for t in topics:
        if t["order_index"] < resolved["order_index"]:
            from leetpath.database.queries import update_topic_state
            update_topic_state(t["id"], status="skipped", started_date=None, completed_date=None)
        elif t["order_index"] == resolved["order_index"]:
            from leetpath.database.queries import update_topic_state
            update_topic_state(t["id"], status="active", started_date=today_str, completed_date=None)
        else:
            from leetpath.database.queries import update_topic_state
            update_topic_state(t["id"], status="locked", started_date=None, completed_date=None, mastery_score=0.0)
            
    set_user_meta("current_topic_id", str(resolved["id"]))
    
    if active:
        from leetpath.assignments.generator import refresh_assignments_for_new_topic
        refresh_assignments_for_new_topic(active["id"], resolved["id"], today_str)
    else:
        generate_daily_assignments(today_str)
        
    console.print(f"✓ Now active: {resolved['name']}")

@app.command(name="revisit")
def revisit(
    topic_name: str = typer.Argument(..., help="Topic name to revisit")
):
    """Revisit a completed topic with extra problems today."""
    check_init()
    today_str = datetime.today().strftime("%Y-%m-%d")
    
    topics = get_all_topics()
    resolved = resolve_topic_name(topic_name, topics)
    if not resolved:
        raise typer.Exit(code=1)
        
    if resolved["status"] not in ["complete", "skipped"]:
        console.print(f"[bold red]Error: '{resolved['name']}' is not yet completed. Use 'dsa move' to jump to it instead.[/bold red]\n")
        raise typer.Exit(code=1)
        
    # Show topic summary
    from leetpath.stats.calculator import calculate_topic_mastery
    mastery = calculate_topic_mastery(resolved["id"])
    
    # Count solved problems in this topic
    from leetpath.database.queries import get_db_conn
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM solve_log WHERE topic_id = ?", (resolved["id"],))
    solved_count = cursor.fetchone()["cnt"]
    conn.close()
    
    console.print(f"{resolved['name']} — Mastery: {mastery:.0f}% | Solved: {solved_count} problems")
    console.print(f"Revisiting will give you up to 5 extra problems from {resolved['name']} today alongside your current assignments.")
    
    confirm = Confirm.ask("Confirm revisit?", default=True)
    if not confirm:
        console.print("[cyan]Revisit cancelled.[/cyan]\n")
        raise typer.Exit()
        
    # Generate revisit assignments
    from leetpath.assignments.generator import generate_revisit_assignments
    success = generate_revisit_assignments(resolved["id"], today_str)
    if success:
        console.print(f"[bold green]✓ Added revisit problems from {resolved['name']} to today's list.[/bold green]\n")
    else:
        console.print(f"[bold red]Failed to generate revisit assignments for {resolved['name']}.[/bold red]\n")

if __name__ == "__main__":
    app()
