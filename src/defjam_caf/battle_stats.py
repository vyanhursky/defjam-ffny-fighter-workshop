"""Standalone final attributes; Story profiles retain their verified training fields."""

from .container import SaveError

KEYS = ("upper", "lower", "speed", "toughness", "health", "charisma")
CAPABILITY = "caf-final-stats-1"
BONUSES = ((2, 0, 0, 1, 0, 0), (0, 2, 1, 0, 0, 0), (0, 1, 0, 0, 2, 0), (1, 0, 0, 2, 0, 0), (0, 0, 2, 0, 1, 0))


def validate(value):
    if not (
        type(value) is dict and set(value) == set(KEYS) and all(type(n) is int and 0 <= n <= 50 for n in value.values())
    ):
        raise SaveError("Final battle attributes need all six integer values in 0–50.")
    return value


def effective(fighter):
    if "final_stats" in fighter:
        return dict(validate(fighter["final_stats"]))
    training = [fighter["stats"][k] for k in KEYS[:-1]] + [0]
    return {
        key: int(
            ((n // 5) * 1.274999976158142 + sum(BONUSES[s][i] for s in fighter["styles"]) * 0.45000001788139343)
            * 3.3333330154418945
            + 0.5
        )
        for i, (key, n) in enumerate(zip(KEYS, training, strict=True))
    }
