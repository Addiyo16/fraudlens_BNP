RULE_WEIGHTS = {
    "HIGH_AMOUNT": 35,
    "NIGHT_TRANSACTION": 15,
    "RAPID_FIRE": 25,
    "NEW_LOCATION": 25,
}


def calculate_risk_score(triggered_rules: list[str]) -> int:
    """
    Add the weights of all triggered rules.
    Score cannot exceed 100.
    """

    score = sum(
        RULE_WEIGHTS.get(rule, 0)
        for rule in triggered_rules
    )

    return min(score, 100)


def get_risk_level(score: int) -> str:
    """
    Convert numerical risk score into
    Low, Medium or High.
    """

    if score <= 29:
        return "Low"

    elif score <= 59:
        return "Medium"

    else:
        return "High"