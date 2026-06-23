# leetpath

> Your terminal-based path through DSA — structured, tracked, placement-ready.

## Overview

leetpath is a fully local, terminal-based tool that structures your DSA
preparation for placement interviews at Indian product companies and FAANG.
It replaces random LeetCode grinding with a structured 16-topic roadmap,
dynamically fetched daily problems, and detailed progress tracking —
all from your terminal with no account or internet dependency beyond
daily problem fetching.

## Features

- 📍 16-topic structured roadmap across 6 months
- 🎯 Two tracks: Placement Core (3 months) + Extended Track (3 months)
- 🔄 Daily dynamic problem fetching from LeetCode (no preset static lists)
- 📈 Difficulty ramp per topic (Easy+Medium → Medium+Hard)
- 📊 Per-topic progress tracking with mastery scoring
- 🔥 Streak tracking and full solve history with approach notes
- ⚙️  Fully customizable roadmap (reorder, add, remove topics, set days)
- ⏭️  Skip or move to any topic at any time
- 🖥️  Clean minimal terminal UI powered by Rich
- 💾 Fully local — all data stored in ~/.leetpath/leetpath.db

## Tech Stack

| Layer     | Tool                              |
|-----------|-----------------------------------|
| Language  | Python 3.10+                      |
| CLI       | Typer                             |
| UI        | Rich                              |
| Storage   | SQLite                            |
| Fetching  | requests + BeautifulSoup          |

## Installation

### Prerequisites
- Python 3.10+
- pip
- Git

### Steps

```bash
git clone https://github.com/vishnudrm/leetpath.git
cd leetpath
pip install -e .
```

### First Run

```bash
dsa start
```

This initializes your database, lets you customize your roadmap,
and generates your first set of daily problems.

## Commands Reference

| Command                       | Description                                        |
|------------------------------|----------------------------------------------------|
| dsa start                    | Initialize or reset the study plan                 |
| dsa                          | Show main dashboard                                |
| dsa today                    | Show today's assigned problems                     |
| dsa log [url]                | Log a solved problem interactively                 |
| dsa roadmap                  | Show full 16-topic roadmap with status             |
| dsa progress                 | Per-topic progress deep dive across all topics     |
| dsa topic \<name\> progress  | All problems and details for a specific topic      |
| dsa stats                    | Overall statistics dashboard                       |
| dsa history                  | Full solve history with optional filters           |
| dsa pending                  | All unsolved problems from past dates              |
| dsa next                     | Advance to the next topic                          |
| dsa move \<topic\>           | Jump to any topic directly                         |
| dsa skip \<topic\>           | Skip one or more topics by name                    |
| dsa reset                    | Wipe all data and start fresh                      |

## Roadmap

### Track 1 — Placement Core (~3 months)

| #  | Topic          | Est. Days |
|----|----------------|-----------|
| 1  | Arrays         | 12        |
| 2  | Strings        | 10        |
| 3  | Hashing        | 8         |
| 4  | Two Pointers   | 7         |
| 5  | Sliding Window | 7         |
| 6  | Binary Search  | 7         |
| 7  | Linked List    | 10        |
| 8  | Stack          | 7         |
| 9  | Trees          | 12        |
| 10 | BST            | 7         |

**--- PLACEMENT READY MILESTONE ---**

### Track 2 — Extended Track (~3 months)

| #  | Topic               | Est. Days |
|----|---------------------|-----------|
| 11 | Queue               | 5         |
| 12 | Heap                | 7         |
| 13 | Graphs              | 14        |
| 14 | Backtracking        | 10        |
| 15 | Dynamic Programming | 21        |
| 16 | Tries               | 7         |

## Architecture

### Project Structure

```
leetpath/
├── cli/
│   └── main.py          — All Typer CLI commands and entry point
├── dashboard/
│   └── render.py        — Rich UI rendering for all screens
├── database/
│   ├── setup.py         — SQLite schema creation and initialization
│   └── queries.py       — All database query functions
├── roadmap/
│   └── engine.py        — Topic progression, mastery, phase logic
├── fetcher/
│   ├── leetcode.py      — LeetCode GraphQL fetcher and scraper
│   └── fallback.py      — Offline fallback problem lists per topic
├── assignments/
│   └── generator.py     — Daily assignment generation logic
├── stats/
│   └── calculator.py    — Streak, mastery, statistics calculations
└── config.py            — Constants, paths, topic slugs, thresholds
```

### Data Flow

1. `dsa start` initializes SQLite DB at ~/.leetpath/leetpath.db
2. Topics seeded into DB with order, estimated days, track, and LeetCode slug
3. Each day, generator.py checks if assignments already exist for today
4. If not: fetcher queries LeetCode by topic slug and difficulty split
5. Problems selected from returned pool, excluding already-solved problems
6. Assignments persisted to DB — same problems shown all day on every run
7. `dsa log` records solve with time taken, local path, and approach note
8. Mastery recalculated after every log (solved / total assigned for topic)
9. Topic auto-completes at 70% mastery, user prompted to run `dsa next`

### SQLite Schema

| Table      | Purpose                                                    |
|------------|------------------------------------------------------------|
| user_meta  | Key-value store: start_date, best_streak, problems_per_day |
| topics     | All 16 topics with status, mastery, dates, track, slug     |
| assignments| Daily problems with assigned date and solved status        |
| solve_log  | Full solve history with time, path, and approach note      |

## Customization

On `dsa start` you can customize:
- **Problems per day** — default 5, range 3–10
- **Reorder topics** — change the sequence of any topic
- **Add topics** — add custom topics with LeetCode tag slug
- **Remove topics** — remove topics you don't need
- **Estimated days** — adjust time allocated per topic
- **Starting topic** — skip ahead if already proficient in early topics

## Data Storage

All data stored locally at:

```
~/.leetpath/leetpath.db
```

No cloud sync. No account required. Fully private and offline.

## Offline Behavior

Daily problem fetching and `dsa log` require internet to query LeetCode.
If network is unavailable, the tool automatically falls back to a built-in
problem list per topic stored in fetcher/fallback.py.

All other commands work fully offline:
dsa, dsa stats, dsa history, dsa progress, dsa roadmap, dsa pending

## Contributing

Contributions are welcome. Fork the repo, make your changes, open a PR.
Keep changes focused — one feature or fix per PR.

## License

MIT License. See LICENSE file.
