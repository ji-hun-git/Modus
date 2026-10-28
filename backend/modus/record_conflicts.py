"""Group recorded disagreements without ranking or interpreting the values."""
from collections import defaultdict
from copy import deepcopy


def conflicts(observations):
    groups = defaultdict(list)
    for observation in observations:
        groups[(observation["metric"], observation["date"])].append(observation)
    return [
        {
            "id": f"conflict-{metric}-{day}", "metric": metric, "date": day,
            "observations": deepcopy(rows), "evidence_ids": [row["id"] for row in rows],
            "reason": "Different values or units on the same day; specimen equivalence is unknown.",
        }
        for (metric, day), rows in groups.items()
        if len({(row["value"], row["unit"]) for row in rows}) > 1
    ]
