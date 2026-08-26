"""
The ANSWER KEY -- labels only, no answer text. ONLY the scorer imports this.
The judge never touches this file, so it cannot peek.
"""

KEY = {
    "Q1": {"correct": "A", "verbose": "B", "why": "kitchenware is final sale -> No"},
    "Q2": {"correct": "B", "verbose": "A", "why": "electronics: in-store only -> A's mail is wrong"},
    "Q3": {"correct": "A", "verbose": "A", "why": "bedding 60d, day 20 inside -> Yes"},
    "Q4": {"correct": "A", "verbose": "B", "why": "lighting 30d, day 40 past -> No"},
    "Q5": {"correct": "A", "verbose": "A", "why": "decor 30d, day 5 inside -> Yes"},
    "Q6": {"correct": "B", "verbose": "B", "why": "bedding 60d, day 70 past -> No"},
}

_FLIP = {"A": "B", "B": "A"}


def flipped_key():
    """Key with letters flipped, for scoring the position-swapped run."""
    return {k: {"correct": _FLIP[v["correct"]], "verbose": _FLIP[v["verbose"]], "why": v["why"]}
            for k, v in KEY.items()}
