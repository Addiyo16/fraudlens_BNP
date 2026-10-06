from app.schemas.schemas import TransactionSchema


def generate_explanation(
    transaction: TransactionSchema,
    rule_results: list[dict]
) -> str:
    """
    Generate a plain-English explanation based only
    on rules that actually triggered.
    """

    reasons = []

    for result in rule_results:

        rule = result["rule"]

        if rule == "HIGH_AMOUNT":

            reasons.append(
                f"₹{transaction.amount:,.2f} is "
                f"{result['multiple']}× this customer's "
                f"historical average of "
                f"₹{result['average_amount']:,.2f}"
            )

        elif rule == "NIGHT_TRANSACTION":

            reasons.append(
                f"the transaction occurred at "
                f"{result['time']}"
            )

        elif rule == "RAPID_FIRE":

            reasons.append(
                f"{result['transaction_count']} transactions "
                f"occurred within "
                f"{result['window_minutes']} minutes"
            )

        elif rule == "NEW_LOCATION":

            reasons.append(
                f"{transaction.city} is a new location "
                f"for this customer"
            )

    if not reasons:
        return ""

    return "Flagged because " + "; ".join(reasons) + "."