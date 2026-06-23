import typer
from datetime import datetime
from typing import Optional
from rich.prompt import Prompt, Confirm
from rich.console import Console

# Import configurations and db layers
from dsa_coach.config import MASTERY_THRESHOLD
from dsa_coach.database.setup import initialize_database, reset_database
from dsa_coach.database.queries import (
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
    get_problems_per_day
)
from dsa_coach.assignments.generator import generate_daily_assignments
from dsa_coach.stats.calculator import (
    update_and_get_streaks,
    calculate_topic_mastery,
    get_overall_stats_data
)
from dsa_coach.roadmap.engine import (
    get_roadmap_progress,
    check_and_update_active_topic,
    advance_to_next_topic,
    resolve_topic_name
)
from dsa_coach.fetcher.leetcode import scrape_leetcode_problem
from dsa_coach.dashboard.render import (
    render_welcome_screen,
    render_dashboard,
    render_today_assignments,
    render_roadmap,
    render_pending_assignments,
    render_progress,
    render_stats,
    render_history,
    render_topic_progress
)

app = typer.Typer(help="DSA Coach: A terminal-based personal DSA preparation assistant.")
console = Console()

def check_init():
    """Ensure database is initialized, otherwise instruct user and exit."""
    if not is_db_initialized():
        console.print("[bold red]Error: DSA Coach is not initialized yet.[/bold red]")
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
    today_assignments = get_assignments_for_date(today_str)
    today_solved = sum(1 for a in today_assignments if a["status"] == "solved")
    today_total = len(today_assignments)
    
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
def start():
    """First-time initialization of the study plan with customization options."""
    today_str = datetime.today().strftime("%Y-%m-%d")
    
    if is_db_initialized():
        confirm_wipe = Confirm.ask(
            "[bold yellow]DSA Coach has already been initialized. Wiping progress will permanently delete all logs. Continue?[/bold yellow]"
        )
        if not confirm_wipe:
            console.print("[cyan]Initialization aborted.[/cyan]\n")
            raise typer.Exit()
            
        console.print("[yellow]Wiping database...[/yellow]")
        reset_database()
        
    console.print("\n[bold green]=== Roadmap Customization ===[/bold green]\n")
    
    # Step 1: Problems per day
    problems_per_day = 5
    while True:
        p_day_str = Prompt.ask("How many problems do you want to solve per day?", default="5")
        try:
            val = int(p_day_str)
            if 3 <= val <= 10:
                problems_per_day = val
                break
            else:
                console.print("[red]Please enter an integer between 3 and 10.[/red]")
        except ValueError:
            console.print("[red]Please enter a valid integer.[/red]")
            
    # Step 2: Customize roadmap
    from dsa_coach.config import TOPIC_CONFIGS
    topics_list = []
    for idx, cfg in enumerate(TOPIC_CONFIGS, start=1):
        topics_list.append({
            "name": cfg["name"],
            "estimated_days": cfg["days"],
            "track": cfg["track"],
            "leetcode_slug": cfg["slug"],
            "status": "locked",
            "started_date": None
        })
        
    customize = Confirm.ask("Do you want to customize the roadmap?", default=False)
    if customize:
        while True:
            console.print("\n[bold cyan]Current Roadmap:[/bold cyan]")
            for idx, t in enumerate(topics_list, start=1):
                console.print(f"  {idx:2d}. {t['name']} ({t['estimated_days']} days, Track {t['track']})")
                
            console.print("\n[bold yellow]Sub-menu:[/bold yellow]")
            console.print("  [1] Reorder topics")
            console.print("  [2] Add a topic")
            console.print("  [3] Remove a topic")
            console.print("  [4] Change estimated days for a topic")
            console.print("  [5] Done — save and start")
            
            choice = Prompt.ask("Choose an option", choices=["1", "2", "3", "4", "5"])
            
            if choice == "1":
                order_str = Prompt.ask("Enter new order as comma-separated numbers (e.g. 1,3,2,4,5...)")
                try:
                    parts = [int(p.strip()) for p in order_str.split(",")]
                    n = len(topics_list)
                    if len(parts) != n:
                        console.print(f"[red]Error: You must include exactly {n} numbers.[/red]")
                        continue
                    if set(parts) != set(range(1, n + 1)):
                        console.print(f"[red]Error: Numbers must be unique and from 1 to {n}.[/red]")
                        continue
                    preview = [topics_list[p - 1] for p in parts]
                    console.print("\n[bold green]Preview of New Order:[/bold green]")
                    for idx, t in enumerate(preview, start=1):
                        console.print(f"  {idx:2d}. {t['name']} ({t['estimated_days']} days)")
                    confirm = Confirm.ask("Confirm this order?", default=True)
                    if confirm:
                        topics_list = preview
                except ValueError:
                    console.print("[red]Error: Invalid format. Please enter comma-separated numbers.[/red]")
                    
            elif choice == "2":
                name = Prompt.ask("Enter topic name")
                slug = Prompt.ask("Enter LeetCode tag slug for this topic (e.g. 'two-pointers')")
                pos_str = Prompt.ask(f"Insert at position (1-{len(topics_list) + 1})")
                days_str = Prompt.ask("Estimated days")
                track_str = Prompt.ask("Track (1 or 2)", choices=["1", "2"])
                
                try:
                    pos = int(pos_str)
                    days = int(days_str)
                    track = int(track_str)
                    if 1 <= pos <= len(topics_list) + 1:
                        new_topic = {
                            "name": name.strip(),
                            "estimated_days": days,
                            "track": track,
                            "leetcode_slug": slug.strip(),
                            "status": "locked",
                            "started_date": None
                        }
                        topics_list.insert(pos - 1, new_topic)
                        console.print(f"[green]Successfully added topic '{name}' at position {pos}.[/green]")
                    else:
                        console.print(f"[red]Error: Position must be between 1 and {len(topics_list) + 1}.[/red]")
                except ValueError:
                    console.print("[red]Error: Invalid position or estimated days.[/red]")
                    
            elif choice == "3":
                num_str = Prompt.ask(f"Enter topic number to remove (1-{len(topics_list)})")
                try:
                    num = int(num_str)
                    if 1 <= num <= len(topics_list):
                        t = topics_list[num - 1]
                        confirm = Confirm.ask(f"Remove '{t['name']}'?", default=False)
                        if confirm:
                            topics_list.pop(num - 1)
                            console.print(f"[green]Successfully removed '{t['name']}'.[/green]")
                    else:
                        console.print(f"[red]Error: Topic number must be between 1 and {len(topics_list)}.[/red]")
                except ValueError:
                    console.print("[red]Error: Invalid topic number.[/red]")
                    
            elif choice == "4":
                num_str = Prompt.ask(f"Enter topic number (1-{len(topics_list)})")
                try:
                    num = int(num_str)
                    if 1 <= num <= len(topics_list):
                        t = topics_list[num - 1]
                        new_days_str = Prompt.ask(f"New estimated days [current: {t['estimated_days']}]")
                        try:
                            new_days = int(new_days_str)
                            t["estimated_days"] = new_days
                            console.print(f"[green]Updated '{t['name']}' to {new_days} days.[/green]")
                        except ValueError:
                            console.print("[red]Error: Invalid estimated days.[/red]")
                    else:
                        console.print(f"[red]Error: Topic number must be between 1 and {len(topics_list)}.[/red]")
                except ValueError:
                    console.print("[red]Error: Invalid topic number.[/red]")
                    
            elif choice == "5":
                from rich.table import Table
                table = Table(title="Final Customized Roadmap", expand=True)
                table.add_column("#", justify="right", width=6)
                table.add_column("Topic Name", justify="left")
                table.add_column("Estimated Days", justify="right", width=18)
                table.add_column("Track", justify="center", width=12)
                table.add_column("LeetCode Slug", justify="left", width=25)
                
                for idx, t in enumerate(topics_list, start=1):
                    table.add_row(str(idx), t["name"], str(t["estimated_days"]), f"Track {t['track']}", t["leetcode_slug"])
                console.print(table)
                
                confirm = Confirm.ask("Save this roadmap and start?", default=True)
                if confirm:
                    break
                    
    # Step 3: Starting topic
    while True:
        starting_topic_input = Prompt.ask("Start from which topic? (press Enter for beginning, or type topic name)", default="")
        if not starting_topic_input:
            topics_list[0]["status"] = "active"
            topics_list[0]["started_date"] = today_str
            for t in topics_list[1:]:
                t["status"] = "locked"
                t["started_date"] = None
            break
        else:
            resolved = resolve_topic_name(starting_topic_input, topics_list)
            if resolved:
                found = False
                for t in topics_list:
                    if t["name"].lower() == resolved["name"].lower():
                        t["status"] = "active"
                        t["started_date"] = today_str
                        found = True
                    elif not found:
                        t["status"] = "skipped"
                        t["started_date"] = None
                    else:
                        t["status"] = "locked"
                        t["started_date"] = None
                break
                
    # Now initialize DB
    initialize_database(today_str, topics_list=topics_list, problems_per_day=problems_per_day)
    
    # Generate today's assignments
    generate_daily_assignments(today_str)
    
    # Render welcome screen
    render_welcome_screen(today_str, problems_per_day=problems_per_day, total_topics=len(topics_list))

@app.command(name="today")
def today():
    """Display today's 5 assigned problems."""
    check_init()
    today_str = datetime.today().strftime("%Y-%m-%d")
    
    # Ensure assignments exist
    assignments = generate_daily_assignments(today_str)
    render_today_assignments(assignments)

@app.command(name="roadmap")
def roadmap():
    """Display the 6-month roadmap of all 16 topics."""
    check_init()
    topics = get_all_topics()
    
    # Refresh mastery score for all topics (so the list shows updated scores)
    for t in topics:
        mastery = calculate_topic_mastery(t["id"])
        # Update in database if status isn't complete/skipped (actually update for accurate roadmap)
        # We can update status to complete if mastery crossed 70% (just in case)
        if t["status"] == "active" and mastery >= 70.0:
            from dsa_coach.database.queries import update_topic_status
            update_topic_status(t["id"], status="complete", completed_date=datetime.today().strftime("%Y-%m-%d"), mastery_score=mastery)
            t["status"] = "complete"
            t["mastery_score"] = mastery
        else:
            from dsa_coach.database.queries import update_topic_status
            update_topic_status(t["id"], status=t["status"], mastery_score=mastery)
            t["mastery_score"] = mastery
            
    # Reload topics for rendering
    topics = get_all_topics()
    _, overall_pct, _ = get_roadmap_progress()
    render_roadmap(topics, overall_pct)

@app.command(name="log")
def log(leetcode_url: Optional[str] = typer.Argument(None)):
    """Log a solved problem using its LeetCode URL."""
    check_init()
    today_str = datetime.today().strftime("%Y-%m-%d")
    
    # Step 1: Prompt for URL if not provided as argument
    if not leetcode_url:
        leetcode_url = typer.prompt("Enter LeetCode URL")
        
    # Normalize URL by removing spaces/slashes
    leetcode_url = leetcode_url.strip()
    
    # Check if duplicate
    existing_solve = get_solve_log_by_url(leetcode_url)
    if existing_solve:
        console.print(f"[bold yellow]Warning: You have already logged this problem: '{existing_solve['title']}' on {existing_solve['solved_date']}.[/bold yellow]")
        console.print("Skipping to avoid duplicate logs.\n")
        raise typer.Exit()
        
    console.print("[cyan]Fetching problem details from LeetCode...[/cyan]")
    title, difficulty = scrape_leetcode_problem(leetcode_url)
    
    if not title or not difficulty:
        console.print("[yellow]Could not automatically fetch problem details.[/yellow]")
        title = Prompt.ask("Please enter the problem title manually")
        difficulty = Prompt.ask(
            "Please enter the difficulty manually",
            choices=["Easy", "Medium", "Hard"]
        )
    else:
        # Step 2: Show problem details
        console.print(f"Problem details: [bold cyan]{title}[/bold cyan] ({difficulty.capitalize()})")
        
    # Capitalize difficulty to match DB standards (Easy/Medium/Hard)
    difficulty = difficulty.capitalize()
    
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
    # Find matching assignment
    assignment = get_assignment_by_url(leetcode_url, status_filter="pending")
    active_topic = get_active_topic()
    
    if not active_topic:
        console.print("[bold red]Error: No active topic found. Cannot log solve.[/bold red]")
        raise typer.Exit(code=1)
        
    if assignment:
        # Mark assignment solved
        mark_assignment_solved(assignment["id"])
        # Insert log linked to assignment
        insert_solve_log(
            assignment_id=assignment["id"],
            title=title,
            url=leetcode_url,
            topic_id=assignment["topic_id"],
            difficulty=difficulty,
            solved_date=today_str,
            time_taken=time_taken,
            local_path=local_path,
            approach_note=approach_note,
            is_assigned=1
        )
        console.print(f"[bold green]Successfully logged assignment: '{title}'![/bold green]")
    else:
        # Check if URL was assigned but already solved, or completely bonus
        # If the URL is in assignments but status is 'solved', it's already solved (prevented by duplicate check though)
        # Log as bonus solve under the active topic
        insert_solve_log(
            assignment_id=None,
            title=title,
            url=leetcode_url,
            topic_id=active_topic["id"],
            difficulty=difficulty,
            solved_date=today_str,
            time_taken=time_taken,
            local_path=local_path,
            approach_note=approach_note,
            is_assigned=0
        )
        console.print(f"[bold green]Successfully logged bonus solve: '{title}' under active topic '{active_topic['name']}'![/bold green]")
        
    # Recalculate topic mastery and update active topic
    check_and_update_active_topic(today_str)
    
    # Re-fetch active topic to see if it changed to complete
    refreshed_active = get_topic_by_id(active_topic["id"])
    if refreshed_active and refreshed_active["status"] == "complete":
        console.print(
            f"\n[bold green]★ Topic threshold reached ({refreshed_active['mastery_score']:.1f}% mastery)! ★[/bold green]\n"
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
        from dsa_coach.database.queries import update_topic_status
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

@app.command(name="next")
def next_topic():
    """Advance to the next sequential topic."""
    check_init()
    today_str = datetime.today().strftime("%Y-%m-%d")
    
    active = get_active_topic()
    if not active:
        console.print("[yellow]No active topic found. Run 'dsa start' to begin.[/yellow]")
        raise typer.Exit()
        
    mastery = calculate_topic_mastery(active["id"])
    
    # Warn user if mastery < 70%
    if mastery < 70.0:
        console.print(f"[bold yellow]Warning: Current topic '{active['name']}' mastery is only {mastery:.1f}% (Required: 70%).[/bold yellow]")
        confirm = Confirm.ask(
            f"You've solved problems in {active['name']}. Advance anyway?"
        )
        if not confirm:
            console.print("[cyan]Staying on active topic.[/cyan]\n")
            raise typer.Exit()
            
        success, msg = advance_to_next_topic(today_str, force=True)
    else:
        success, msg = advance_to_next_topic(today_str, force=False)
        
    if success:
        console.print(f"[bold green]{msg}[/bold green]\n")
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
    if not active:
        console.print("[yellow]No active topic found. Run 'dsa start' to begin.[/yellow]")
        raise typer.Exit()
        
    if resolved["id"] == active["id"]:
        console.print(f"Already on {resolved['name']}. No change made.\n")
        raise typer.Exit()
        
    if resolved["order_index"] < active["order_index"]:
        # Target is behind
        confirm = Confirm.ask(
            f"Move back to {resolved['name']}? This will reset progress on {active['name']}."
        )
        if not confirm:
            console.print("[cyan]Move aborted.[/cyan]\n")
            raise typer.Exit()
            
        # Update topics
        for t in topics:
            if t["order_index"] > resolved["order_index"]:
                from dsa_coach.database.queries import update_topic_state
                update_topic_state(t["id"], status="locked", started_date=None, completed_date=None, mastery_score=0.0)
            elif t["order_index"] == resolved["order_index"]:
                from dsa_coach.database.queries import update_topic_state
                update_topic_state(t["id"], status="active", started_date=today_str, completed_date=None)
                
        set_user_meta("current_topic_id", str(resolved["id"]))
        
        # Clear daily assignments for today and regenerate for the new active topic
        from dsa_coach.database.queries import delete_assignments_for_date
        delete_assignments_for_date(today_str)
        generate_daily_assignments(today_str)
        
        console.print(f"[green]Moved back to topic {resolved['order_index']}: {resolved['name']}. Fresh assignments generated![/green]\n")
        show_dashboard(today_str)
        
    else:
        # Target is ahead
        # Determine intermediate topics to mark skipped
        intermediate = []
        for t in topics:
            if active["order_index"] <= t["order_index"] < resolved["order_index"]:
                intermediate.append(t)
                
        intermediate_names = ", ".join([t["name"] for t in intermediate])
        console.print(f"Moving from {active['name']} → {resolved['name']}. {intermediate_names} will be marked skipped.")
        
        confirm = Confirm.ask("Confirm move?", default=False)
        if not confirm:
            console.print("[cyan]Move aborted.[/cyan]\n")
            raise typer.Exit()
            
        # Update topics
        for t in topics:
            if t["order_index"] < resolved["order_index"]:
                if t["status"] not in ["complete", "skipped"]:
                    from dsa_coach.database.queries import update_topic_state
                    update_topic_state(t["id"], status="skipped", started_date=None, completed_date=None)
            elif t["order_index"] == resolved["order_index"]:
                from dsa_coach.database.queries import update_topic_state
                update_topic_state(t["id"], status="active", started_date=today_str, completed_date=None)
            else:
                from dsa_coach.database.queries import update_topic_state
                update_topic_state(t["id"], status="locked", started_date=None, completed_date=None, mastery_score=0.0)
                
        set_user_meta("current_topic_id", str(resolved["id"]))
        
        # Clear daily assignments for today and regenerate for the new active topic
        from dsa_coach.database.queries import delete_assignments_for_date
        delete_assignments_for_date(today_str)
        generate_daily_assignments(today_str)
        
        console.print(f"[green]Moved to topic {resolved['order_index']}: {resolved['name']}. Fresh assignments generated![/green]\n")
        show_dashboard(today_str)

if __name__ == "__main__":
    app()
