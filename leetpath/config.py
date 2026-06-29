import os
import math

# SQLite database configuration
DB_DIR = os.path.expanduser("~/.leetpath")
DB_PATH = os.path.join(DB_DIR, "leetpath.db")

# Target mastery threshold (100% for NeetCode)
MASTERY_THRESHOLD = 1.0

# List of 18 NeetCode 150 categories with estimated days (based on 2 problems/day) and slugs
TOPIC_CONFIGS = [
    {"name": "Arrays & Hashing", "days": 5, "track": 1, "slug": "array"},
    {"name": "Two Pointers", "days": 3, "track": 1, "slug": "two-pointers"},
    {"name": "Sliding Window", "days": 3, "track": 1, "slug": "sliding-window"},
    {"name": "Stack", "days": 3, "track": 1, "slug": "stack"},
    {"name": "Binary Search", "days": 4, "track": 1, "slug": "binary-search"},
    {"name": "Linked List", "days": 6, "track": 1, "slug": "linked-list"},
    {"name": "Trees", "days": 8, "track": 1, "slug": "tree"},
    {"name": "Heap / Priority Queue", "days": 4, "track": 1, "slug": "heap-priority-queue"},
    {"name": "Backtracking", "days": 5, "track": 1, "slug": "backtracking"},
    {"name": "Tries", "days": 2, "track": 1, "slug": "trie"},
    {"name": "Graphs", "days": 7, "track": 1, "slug": "graph"},
    {"name": "Advanced Graphs", "days": 3, "track": 1, "slug": "advanced-graphs"},
    {"name": "1-D Dynamic Programming", "days": 6, "track": 1, "slug": "1d-dynamic-programming"},
    {"name": "2-D Dynamic Programming", "days": 6, "track": 1, "slug": "2d-dynamic-programming"},
    {"name": "Greedy", "days": 4, "track": 1, "slug": "greedy"},
    {"name": "Intervals", "days": 3, "track": 1, "slug": "intervals"},
    {"name": "Math & Geometry", "days": 4, "track": 1, "slug": "math-geometry"},
    {"name": "Bit Manipulation", "days": 4, "track": 1, "slug": "bit-manipulation"}
]
