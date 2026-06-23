import math
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress_bar import ProgressBar
from rich.columns import Columns

console = Console()

def render_welcome_screen(start_date: str, problems_per_day: int = 5, total_topics: int = 16):
    """Render the welcome screen for first-time initialization."""
    title_text = Text("\nWelcome to leetpath!", style="bold cyan")
    body_text = Text(
        f"\nYour personal terminal-based assistant for placement preparation (Indian Product Companies + FAANG).\n"
        f"Study Plan started on: {start_date}\n\n"
        f"Key Rules:\n"
        f"1. Study {total_topics} topics sequentially across 2 tracks.\n"
        f"2. Daily problems: {problems_per_day} fresh challenges each day.\n"
        f"3. Mastery: Reach >= 70% master score on a topic to unlock the next (or run 'dsa next').\n"
        f"4. Track 2 unlocks only when all Track 1 topics are complete or skipped.\n\n"
        f"Run 'dsa' to view your dashboard, 'dsa today' for daily problems, or 'dsa --help' for commands.\n",
        style="white"
    )
    welcome_panel = Panel(
        Text.assemble(title_text, body_text),
        title="[bold cyan]leetpath Initialized[/bold cyan]",
        border_style="cyan",
        expand=False,
        padding=(1, 3)
    )
    console.print(welcome_panel)

def get_difficulty_colored(difficulty: str) -> Text:
    """Return colored difficulty text."""
    diff = difficulty.capitalize()
    if diff == "Easy":
        return Text(diff, style="green")
    elif diff == "Medium":
        return Text(diff, style="yellow")
    elif diff == "Hard":
        return Text(diff, style="red")
    return Text(diff)

def get_status_colored(status: str) -> Text:
    """Return status styled with clean indicators."""
    stat = status.lower()
    if stat == "solved":
        return Text("✓ Solved", style="bold green")
    elif stat == "pending":
        return Text("○ Pending", style="bold yellow")
    return Text(status)

def draw_mini_progress_bar(completed: int, total: int, width: int = 15) -> str:
    """Draw a text-based minimal progress bar."""
    if total == 0:
        return "[          ]"
    filled = int((completed / total) * width)
    unfilled = width - filled
    return f"[{'#' * filled}{' ' * unfilled}]"

def render_dashboard(
    day_num: int,
    today_date: str,
    active_topic: dict | None,
    days_elapsed: int,
    today_solved: int,
    today_total: int,
    current_streak: int,
    best_streak: int,
    track1_pct: float,
    overall_pct: float,
    placement_ready: bool
):
    """Render the main CLI dashboard in a single clean screen."""
    # Header
    header = Table.grid(expand=True)
    header.add_column(justify="left")
    header.add_column(justify="right")
    
    badge = " [bold green]Placement Ready ✓[/bold green]" if placement_ready else ""
    header.add_row(
        Text.from_markup(f"leetpath | Day {day_num}{badge}", style="bold cyan"),
        Text(today_date, style="dim white")
    )
    console.print(header)
    console.print("-" * 65, style="dim white")
    
    # Active Topic Section
    pending_start_topic = None
    completed_topic = None
    
    # Try to find pending_start topic if active_topic is None
    if not active_topic:
        from leetpath.database.queries import get_db_conn
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM topics WHERE status = 'pending_start' LIMIT 1")
        pending_start_topic = cursor.fetchone()
        if pending_start_topic:
            cursor.execute("SELECT * FROM topics WHERE order_index < ? AND status IN ('complete', 'skipped') ORDER BY order_index DESC LIMIT 1", (pending_start_topic["order_index"],))
            completed_topic = cursor.fetchone()
        conn.close()
        
    if active_topic:
        from leetpath.database.queries import get_problems_per_day
        from leetpath.assignments.generator import get_difficulty_split
        problems_per_day = get_problems_per_day()
        diff_split = get_difficulty_split(days_elapsed, active_topic["estimated_days"], problems_per_day)
        
        parts = []
        for diff in ["Easy", "Medium", "Hard"]:
            cnt = diff_split.get(diff, 0)
            if cnt > 0:
                parts.append(f"{cnt} {diff if diff != 'Medium' else 'Med'}")
        diff_desc = ", ".join(parts)
        
        halfway = math.ceil(active_topic["estimated_days"] / 2.0)
        phase_name = "First Half" if days_elapsed <= halfway else "Second Half"
        phase_str = f"{phase_name} ({diff_desc})"
        
        topic_info = Text.assemble(
            "Topic: ", Text(active_topic['name'], style="bold yellow"), f" (Track {active_topic['track']})\n",
            f"Phase: {phase_str}\n",
            f"Time spent: {days_elapsed} / {active_topic['estimated_days']} days elapsed"
        )
        topic_panel = Panel(topic_info, title="[bold cyan]Active Focus[/bold cyan]", border_style="cyan", expand=True)
    elif pending_start_topic:
        completed_name = completed_topic["name"] if completed_topic else "Previous Topic"
        scheduled_start = pending_start_topic["scheduled_start_date"] or "tomorrow"
        rest_info = Text.assemble(
            "Today's topic: ", Text(f"{completed_name} — Done ✓", style="bold green"), "\n",
            "Next up: ", Text(pending_start_topic["name"], style="bold yellow"), "\n",
            f"Starts tomorrow: {scheduled_start}\n",
            "Take a break. You earned it."
        )
        topic_panel = Panel(rest_info, title="[bold cyan]Rest Day[/bold cyan]", border_style="cyan", expand=True)
    else:
        topic_info = Text("Active Topic: None\nRun 'dsa start' or check 'dsa progress'.")
        topic_panel = Panel(topic_info, title="[bold cyan]Active Focus[/bold cyan]", border_style="cyan", expand=True)
        
    # Today's Progress Section
    progress_bar_str = draw_mini_progress_bar(today_solved, today_total, width=15)
    today_progress_info = Text.assemble(
        f"Today's Solve Progress: {today_solved}/{today_total} Solved\n",
        "Progress: ", Text(progress_bar_str, style="cyan"), "\n",
        f"Streak: {current_streak} days (Best: {best_streak} days)"
    )
    
    # Panel layout
    progress_panel = Panel(today_progress_info, title="[bold cyan]Daily Stats[/bold cyan]", border_style="cyan", expand=True)
    
    # Tracks Progress Section
    track_details = Text.assemble(
        f"Track 1 (Placement Core): {track1_pct:.1f}%\n",
        f"Overall 6-Month Roadmap:  {overall_pct:.1f}%"
    )
    tracks_panel = Panel(track_details, title="[bold cyan]Roadmap Progress[/bold cyan]", border_style="cyan", expand=True)
    
    # Print layout
    console.print(Columns([topic_panel, progress_panel]))
    console.print(tracks_panel)
    console.print()
    console.print(Text("Commands: dsa today | dsa log <url> | dsa roadmap | dsa stats | dsa pending", style="dim white"))

def math_ceil_half(num: int) -> int:
    """Helper to do ceil of num/2."""
    import math
    return math.ceil(num / 2.0)

def get_today_progress_stats(today_str: str) -> tuple[int, int]:
    """Get count of solved and total active assignments for today."""
    from leetpath.database.queries import get_db_conn
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM assignments WHERE assigned_date = ? AND status = 'solved'", (today_str,))
    solved = cursor.fetchone()["cnt"]
    cursor.execute("SELECT COUNT(*) as cnt FROM assignments WHERE assigned_date = ? AND status != 'skipped'", (today_str,))
    total = cursor.fetchone()["cnt"]
    conn.close()
    return solved, total

def render_today_assignments(assignments: list[dict]):
    """Render today's assignments in a table."""
    active_assignments = [a for a in assignments if a["status"] != 'skipped']
    if not active_assignments:
        console.print("[yellow]No assignments found for today. Generate using 'dsa' or 'dsa start'[/yellow]")
        return
        
    regular = [a for a in active_assignments if not a.get("is_revisit")]
    revisits = [a for a in active_assignments if a.get("is_revisit")]
        
    table = Table(title="[bold cyan]Today's Daily Assignments[/bold cyan]", border_style="cyan", expand=True)
    table.add_column("#", justify="center", width=6)
    table.add_column("Problem Name", justify="left")
    table.add_column("Difficulty", justify="center", width=15)
    table.add_column("Status", justify="center", width=15)
    
    for idx, ass in enumerate(regular, start=1):
        status = ass["status"]
        table.add_row(
            str(idx),
            ass["title"],
            get_difficulty_colored(ass["difficulty"]),
            get_status_colored(status)
        )
        
    if revisits:
        from leetpath.database.queries import get_topic_by_id
        current_topic_id = None
        revisit_idx = len(regular) + 1
        for ass in revisits:
            if ass["topic_id"] != current_topic_id:
                current_topic_id = ass["topic_id"]
                topic = get_topic_by_id(current_topic_id)
                topic_name = topic["name"] if topic else "Unknown Topic"
                table.add_row(
                    "",
                    f"[dim]── Revisit: {topic_name} ──[/dim]",
                    "",
                    ""
                )
            status = ass["status"]
            table.add_row(
                str(revisit_idx),
                ass["title"],
                get_difficulty_colored(ass["difficulty"]),
                get_status_colored(status)
            )
            revisit_idx += 1
            
    today_str = datetime.today().strftime('%Y-%m-%d')
    solved_today, total_today = get_today_progress_stats(today_str)
        
    console.print(table)
    console.print(f"\n[bold cyan]Summary:[/bold cyan] {solved_today}/{total_today} solved today.\n")

def render_roadmap(topics: list[dict], overall_pct: float):
    """Render the roadmap with Track dividers and milestone marker."""
    table = Table(title=f"[bold cyan]leetpath Roadmap ({len(topics)} Topics)[/bold cyan]", border_style="cyan", expand=True)
    table.add_column("#", justify="center", width=4)
    table.add_column("Topic", justify="left")
    table.add_column("Track", justify="center", width=8)
    table.add_column("Est. Days", justify="center", width=10)
    table.add_column("Mastery", justify="center", width=10)
    table.add_column("Status", justify="center", width=12)
    
    # We will split by Track 1 and Track 2, and insert milestone marker
    current_track = 1
    
    # Track 1 Header row
    table.add_row("", "[bold cyan]--- TRACK 1: PLACEMENT CORE ---[/bold cyan]", "", "", "", "")
    
    for idx, t in enumerate(topics, start=1):
        if t["track"] == 2 and current_track == 1:
            # Placement Ready Milestone Marker
            table.add_row(
                "", 
                "[bold green]================ PLACEMENT READY MILESTONE ================[/bold green]", 
                "", "", "", ""
            )
            table.add_row("", "[bold cyan]--- TRACK 2: EXTENDED TRACK ---[/bold cyan]", "", "", "", "")
            current_track = 2
            
        status_style = "white"
        status_text = t["status"].capitalize()
        
        if t["status"] == "complete":
            status_style = "green"
        elif t["status"] == "active":
            status_style = "bold yellow"
        elif t["status"] == "skipped":
            status_style = "dim red"
        elif t["status"] == "locked":
            status_style = "dim white"
            
        table.add_row(
            str(t["order_index"]),
            t["name"],
            f"Track {t['track']}",
            f"{t['estimated_days']} days",
            f"{t['mastery_score']:.1f}%",
            Text(status_text, style=status_style)
        )
        
    console.print(table)
    console.print(f"\n[bold cyan]Overall Completion:[/bold cyan] {overall_pct:.1f}% of roadmap completed.\n")

def render_pending_assignments(assignments: list[dict]):
    """Render all pending assignments from all past dates grouped by date."""
    if not assignments:
        console.print("[green]Awesome! You have no pending assignments from past days.[/green]\n")
        return
        
    table = Table(title="[bold red]Pending Past Assignments[/bold red]", border_style="red", expand=True)
    table.add_column("Assigned Date", justify="center", width=18)
    table.add_column("Topic", justify="left", width=20)
    table.add_column("Problem Name", justify="left")
    table.add_column("Difficulty", justify="center", width=15)
    
    for ass in assignments:
        table.add_row(
            ass["assigned_date"],
            ass["topic_name"],
            ass["title"],
            get_difficulty_colored(ass["difficulty"])
        )
        
    console.print(table)
    console.print("\n[dim]Run `dsa log` to interactively log solutions for any of these pending problems.[/dim]\n")

def render_progress(topics: list[dict], placement_ready: bool):
    """Render per-topic progress report."""
    console.print(Text("leetpath Progress Deep-Dive", style="bold cyan"))
    console.print()
    
    current_track = 1
    console.print(Text("--- Track 1: Placement Core ---", style="cyan"))
    console.print()
    
    for idx, t in enumerate(topics, start=1):
        if t["track"] == 2 and current_track == 1:
            badge = " [Placement Ready ✓]" if placement_ready else ""
            console.print()
            console.print(Text(f"================ PLACEMENT READY MILESTONE{badge} ================", style="bold green"))
            console.print()
            console.print(Text("--- Track 2: Extended Track ---", style="cyan"))
            console.print()
            current_track = 2
            
        status = t["status"]
        name = t["name"]
        mastery = t["mastery_score"]
        
        # Color coding rows
        if status == "active":
            row_prefix = Text("► ", style="bold yellow")
            style = "bold yellow"
            details = Text.assemble(" - Active | Days Spent: ", Text(f"{t['estimated_days']} days planned", style="yellow"))
        elif status == "complete":
            row_prefix = Text("✓ ", style="green")
            style = "green"
            details = Text(f" - Completed | Started: {t['started_date']} | Done: {t['completed_date']}", style="dim white")
        elif status == "skipped":
            row_prefix = Text("✖ ", style="dim red")
            style = "dim red"
            details = Text(f" - Skipped | Started: {t['started_date']} | Done: {t['completed_date']}", style="dim white")
        else:
            row_prefix = Text("  ", style="dim white")
            style = "dim white"
            details = Text(" - Locked", style="dim white")
            
        progress_bar = draw_mini_progress_bar(int(mastery), 100, width=10)
        
        line_text = Text.assemble(
            row_prefix,
            Text(f"{t['order_index']}. {name:<18}", style=style),
            Text(f"Mastery: {mastery:>5.1f}% {progress_bar}", style=style),
            details
        )
        console.print(line_text)
    console.print()

def render_stats(stats: dict):
    """Render overall statistics dashboard."""
    console.print("[bold cyan]leetpath Statistics Dashboard[/bold cyan]\n")
    
    diff_counts = stats["diff_counts"]
    avg_times = stats["avg_times"]
    
    # 1. Overall stats panel
    overall_info = (
        f"Total Problems Solved: [bold green]{stats['total_solved']}[/bold green]\n"
        f"Total Solve Time:      {stats['total_time_spent']} minutes\n"
        f"Days Active:           {stats['days_active']} days\n"
        f"Current Streak:        {stats['current_streak']} days\n"
        f"Best Streak:           {stats['best_streak']} days\n"
        f"Most Productive Day:   {stats['most_productive_day']}"
    )
    overall_panel = Panel(overall_info, title="[bold cyan]Summary Metrics[/bold cyan]", border_style="cyan", expand=True)
    
    # 2. Difficulty breakdown panel
    diff_info = (
        f"Easy:   [bold green]{diff_counts['Easy']}[/bold green] (Avg solve time: {avg_times['Easy']:.1f} min)\n"
        f"Medium: [bold yellow]{diff_counts['Medium']}[/bold yellow] (Avg solve time: {avg_times['Medium']:.1f} min)\n"
        f"Hard:   [bold red]{diff_counts['Hard']}[/bold red] (Avg solve time: {avg_times['Hard']:.1f} min)"
    )
    diff_panel = Panel(diff_info, title="[bold cyan]Difficulty Breakdown[/bold cyan]", border_style="cyan", expand=True)
    
    console.print(Columns([overall_panel, diff_panel]))
    console.print()

def render_history(history_logs: list[dict]):
    """Render filtered solve history table."""
    if not history_logs:
        console.print("[yellow]No solve logs match your filters.[/yellow]\n")
        return
        
    table = Table(title="[bold cyan]Solve History Log[/bold cyan]", border_style="cyan")
    table.add_column("Date", justify="center", width=12)
    table.add_column("Problem Name", justify="left", width=25)
    table.add_column("Topic", justify="left", width=15)
    table.add_column("Difficulty", justify="center", width=12)
    table.add_column("Time (min)", justify="center", width=10)
    table.add_column("Approach Note", justify="left", width=30)
    
    for log in history_logs:
        approach = log["approach_note"] or ""
        approach_summary = approach[:30] if len(approach) > 30 else approach
            
        table.add_row(
            log["solved_date"],
            log["title"],
            log["topic_name"],
            get_difficulty_colored(log["difficulty"]),
            str(log["time_taken_minutes"] or "-"),
            approach_summary
        )
        
    console.print(table)
    console.print()

def draw_mini_progress_bar_custom(completed: int, total: int, width: int = 10) -> str:
    """Draw a text-based minimal progress bar using blocks."""
    if total == 0:
        return f"[{'░' * width}]"
    filled = int(round((completed / total) * width))
    unfilled = width - filled
    return f"[{'█' * filled}{'░' * unfilled}]"

def render_topic_progress(topic: dict, solves: list[dict], assignments: list[dict], problems_per_day: int):
    """Render details of a specific topic including solved and pending problems."""
    # 1. Calculate mastery and days elapsed
    solved_count = len(solves)
    estimated_days = topic["estimated_days"]
    total_expected = estimated_days * problems_per_day
    mastery_pct = calculate_topic_mastery(topic["id"])
    
    # Days elapsed
    days_elapsed = 0
    if topic["started_date"]:
        started_dt = datetime.strptime(topic["started_date"], "%Y-%m-%d")
        if topic["completed_date"]:
            end_dt = datetime.strptime(topic["completed_date"], "%Y-%m-%d")
        else:
            end_dt = datetime.today()
        days_elapsed = max(1, (end_dt - started_dt).days + 1)
        
    # Phase calculation
    halfway = math.ceil(estimated_days / 2.0)
    if days_elapsed <= halfway:
        phase = "First Half"
    else:
        phase = "Second Half"
        
    # Draw mastery bar
    mastery_bar = draw_mini_progress_bar_custom(solved_count, total_expected, width=10)
    
    # Construct summary text
    status_text = topic["status"].capitalize()
    summary_text = (
        f"Topic: {topic['name']} | Track: {topic['track']} | Status: {status_text}\n"
        f"Mastery: {solved_count}/{total_expected} expected ({mastery_pct:.1f}%) {mastery_bar}\n"
        f"Phase: {phase} | Days elapsed: {days_elapsed}/{estimated_days}"
    )
    
    summary_panel = Panel(
        Text(summary_text, style="white"),
        title=f"[bold cyan]Topic Progress Summary: {topic['name']}[/bold cyan]",
        border_style="cyan",
        expand=False,
        padding=(1, 3)
    )
    console.print(summary_panel)
    console.print()
    
    # Section 1 — Solved Problems
    console.print(Text("Section 1 — Solved Problems", style="bold green"))
    if not solves:
        console.print("[dim]No solved problems found for this topic.[/dim]\n")
    else:
        table_solved = Table(border_style="green", expand=True)
        table_solved.add_column("#", justify="center", width=6)
        table_solved.add_column("Problem Name", justify="left", ratio=3)
        table_solved.add_column("Difficulty", justify="center", width=15)
        table_solved.add_column("Solve Date", justify="center", width=15)
        table_solved.add_column("Time Taken (min)", justify="center", width=20)
        table_solved.add_column("Approach Note", justify="left", ratio=4)
        
        for idx, solve in enumerate(solves, start=1):
            table_solved.add_row(
                str(idx),
                solve["title"],
                get_difficulty_colored(solve["difficulty"]),
                solve["solved_date"],
                f"{solve['time_taken_minutes']} min" if solve["time_taken_minutes"] else "0 min",
                solve["approach_note"] or ""
            )
        console.print(table_solved)
        console.print()
        
    # Section 2 — Pending / Upcoming
    console.print(Text("Section 2 — Pending / Upcoming", style="bold yellow"))
    pending_assignments = [a for a in assignments if a["status"] == "pending"]
    if not pending_assignments:
        console.print("[dim]No pending or upcoming problems for this topic.[/dim]\n")
    else:
        table_pending = Table(border_style="yellow", expand=True)
        table_pending.add_column("#", justify="center", width=6)
        table_pending.add_column("Problem Name", justify="left")
        table_pending.add_column("Difficulty", justify="center", width=15)
        table_pending.add_column("Assigned Date", justify="center", width=15)
        table_pending.add_column("Status", justify="center", width=15)
        
        for idx, ass in enumerate(pending_assignments, start=1):
            table_pending.add_row(
                str(idx),
                ass["title"],
                get_difficulty_colored(ass["difficulty"]),
                ass["assigned_date"],
                get_status_colored(ass["status"])
            )
        console.print(table_pending)
        console.print()
