# leetpath

> Your terminal-based path through the NeetCode 150 — structured, tracked, offline-first.

## Overview

`leetpath` is a fully local, terminal-based tool that structures your DSA preparation based on the **NeetCode 150** curriculum. It replaces random LeetCode grinding with a strict daily quota of 2 problems, a sequential category-by-category roadmap, 100% category completion tracking, and offline-first progress logging.

## Features

- 📍 **18-category structured roadmap** covering the entire NeetCode 150 curriculum
- 🎯 **Strict daily cadence** of 2 problems per day
- 🔄 **Fully sequential and static** problem assignment sequence in NeetCode order
- 📊 **Per-category progress tracking** requiring 100% completion (mastery) to advance
- 🔥 **Streak tracking** and full solve history with approach notes
- ⏭️ **Skip or jump** to any category at any time using `dsa move`
- 🖥️ **Clean minimal terminal UI** powered by Rich
- 💾 **100% local and offline** — all data stored in `~/.leetpath/leetpath.db`

## Tech Stack

| Layer     | Tool                              |
|-----------|-----------------------------------|
| Language  | Python 3.10+                      |
| CLI       | Typer                             |
| UI        | Rich                              |
| Storage   | SQLite                            |

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

This initializes your database and sets up your study plan starting from tomorrow.

## Commands Reference

| Command                       | Description                                        |
|------------------------------|----------------------------------------------------|
| `dsa start`                  | Initialize or reset the study plan (starts tomorrow)|
| `dsa`                        | Show main dashboard                                |
| `dsa today`                  | Show today's assigned problems                     |
| `dsa log [url]`              | Log a solved NeetCode 150 problem by LeetCode URL  |
| `dsa roadmap`                | Show full 18-category roadmap with status          |
| `dsa progress`               | Per-category progress deep dive across all topics  |
| `dsa topic <name> progress`  | All problems and details for a specific topic      |
| `dsa stats`                  | Overall statistics dashboard                       |
| `dsa history`                | Full solve history with optional filters           |
| `dsa pending`                | All unsolved problems from past dates              |
| `dsa next`                   | Advance to the next topic                          |
| `dsa move <topic>`           | Jump the active topic to any topic                 |
| `dsa revisit <topic>`        | Revisit a completed topic with extra daily tasks   |
| `dsa reset`                  | Wipe all data and start fresh                      |

## Roadmap

The 18 NeetCode 150 categories in sequential study order:

| #  | Category                 | Problems | Est. Days |
|----|--------------------------|----------|-----------|
| 1  | Arrays & Hashing         | 9        | 5         |
| 2  | Two Pointers             | 5        | 3         |
| 3  | Sliding Window           | 6        | 3         |
| 4  | Stack                    | 6        | 3         |
| 5  | Binary Search            | 7        | 4         |
| 6  | Linked List              | 11       | 6         |
| 7  | Trees                    | 15       | 8         |
| 8  | Heap / Priority Queue    | 7        | 4         |
| 9  | Backtracking             | 10       | 5         |
| 10 | Tries                    | 3        | 2         |
| 11 | Graphs                   | 13       | 7         |
| 12 | Advanced Graphs          | 6        | 3         |
| 13 | 1-D Dynamic Programming  | 12       | 6         |
| 14 | 2-D Dynamic Programming  | 11       | 6         |
| 15 | Greedy                   | 8        | 4         |
| 16 | Intervals                | 6        | 3         |
| 17 | Math & Geometry          | 8        | 4         |
| 18 | Bit Manipulation         | 7        | 4         |

Total: **150 problems**

## Architecture

### Project Structure

```
leetpath/
├── cli/
│   └── main.py          — All Typer CLI commands and entry point
├── dashboard/
│   └── render.py        — Rich UI rendering for all dashboard screens
├── database/
│   ├── setup.py         — SQLite schema creation and initialization
│   └── queries.py       — All database query functions
├── roadmap/
│   ├── engine.py        — Topic progression, mastery checks
│   └── neetcode150.py   — Hardcoded NeetCode 150 problems
├── fetcher/
│   └── leetcode.py      — LeetCode URL helper functions
├── assignments/
│   └── generator.py     — Sequential daily assignment selection
└── stats/
    └── calculator.py    — Streak, mastery, and statistics calculations
```

### Data Flow

1. `dsa start` wipes the local database at `~/.leetpath/leetpath.db` and schedules the study plan starting tomorrow.
2. Each day, the generator assigns the next 2 unsolved problems in sequence for the active category.
3. `dsa log` matches the logged URL against the static NeetCode 150 dataset offline to record progress.
4. Mastery updates after every solve. Once 100% of problems in a category are solved, the user runs `dsa next` to advance.

### SQLite Schema

| Table      | Purpose                                                    |
|------------|------------------------------------------------------------|
| user_meta  | Key-value store: start_date, best_streak, problems_per_day |
| topics     | All 18 topics with status, mastery, dates, track, slug     |
| assignments| Daily problems with assigned date and solved status        |
| solve_log  | Full solve history with time, path, and approach note      |

## Customization

On `dsa start`, you can specify a starting category using the `--topic` flag if you want to skip ahead:
```bash
dsa start --topic "Trees"
```

## Data Storage

All data is stored locally at:
```
~/.leetpath/leetpath.db
```
No account or internet connectivity is required. Fully private and offline.

## License

MIT License. See LICENSE file.
