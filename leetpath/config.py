import os

# SQLite database configuration
DB_DIR = os.path.expanduser("~/.leetpath")
DB_PATH = os.path.join(DB_DIR, "leetpath.db")

# Target mastery threshold (70%)
MASTERY_THRESHOLD = 0.70

# List of 16 topics with estimated days, track, and LeetCode slugs
TOPIC_CONFIGS = [
    # Track 1 - Placement Core (Topics 1 - 10)
    {"name": "Arrays", "days": 12, "track": 1, "slug": "array"},
    {"name": "Strings", "days": 10, "track": 1, "slug": "string"},
    {"name": "Hashing", "days": 8, "track": 1, "slug": "hash-table"},
    {"name": "Two Pointers", "days": 7, "track": 1, "slug": "two-pointers"},
    {"name": "Sliding Window", "days": 7, "track": 1, "slug": "sliding-window"},
    {"name": "Binary Search", "days": 7, "track": 1, "slug": "binary-search"},
    {"name": "Linked List", "days": 10, "track": 1, "slug": "linked-list"},
    {"name": "Stack", "days": 7, "track": 1, "slug": "stack"},
    {"name": "Trees", "days": 12, "track": 1, "slug": "tree"},
    {"name": "BST", "days": 7, "track": 1, "slug": "binary-search-tree"},

    # Track 2 - Extended Track (Topics 11 - 16)
    {"name": "Queue", "days": 5, "track": 2, "slug": "queue"},
    {"name": "Heap", "days": 7, "track": 2, "slug": "heap-priority-queue"},
    {"name": "Graphs", "days": 14, "track": 2, "slug": "graph"},
    {"name": "Backtracking", "days": 10, "track": 2, "slug": "backtracking"},
    {"name": "Dynamic Prog.", "days": 21, "track": 2, "slug": "dynamic-programming"},
    {"name": "Tries", "days": 7, "track": 2, "slug": "trie"}
]
