from datetime import timedelta

from app.schemas.schemas import TransactionSchema
from app.services.scoring import calculate_risk_score, get_risk_level
from app.services.explanations import generate_explanation


# Minimum number of previous transactions required
# before HIGH_AMOUNT can be evaluated.
MIN_HIGH_AMOUNT_HISTORY = 3


def detect_high_amount(
    transaction: TransactionSchema,
    history: list[TransactionSchema]
):
    """
    HIGH_AMOUNT rule:
    Flag when the current amount is more than 5 times
    the customer's historical average.

    At least 3 previous transactions are required.
    """

    if len(history) < MIN_HIGH_AMOUNT_HISTORY:
        return None

    average_amount = sum(
        txn.amount for txn in history
    ) / len(history)

    if transaction.amount > 5 * average_amount:

        multiple = transaction.amount / average_amount

        return {
            "rule": "HIGH_AMOUNT",
            "current_amount": transaction.amount,
            "average_amount": round(average_amount, 2),
            "multiple": round(multiple, 1)
        }

    return None


def detect_night_transaction(
    transaction: TransactionSchema
):
    """
    NIGHT_TRANSACTION rule:
    Flag transactions occurring from 12:00 AM
    up to but not including 5:00 AM.
    """

    hour = transaction.timestamp.hour

    if 0 <= hour < 5:

        return {
            "rule": "NIGHT_TRANSACTION",
            "time": transaction.timestamp.strftime("%I:%M %p")
        }

    return None


def detect_rapid_fire(
    transaction: TransactionSchema,
    history: list[TransactionSchema]
):
    """
    RAPID_FIRE rule:
    Flag when there are at least 3 transactions
    for the same customer within 10 minutes.

    Since 'transaction' is the current transaction,
    we need at least 2 earlier transactions in the
    previous 10-minute window.
    """

    window_start = transaction.timestamp - timedelta(minutes=10)

    recent_transactions = [
        txn
        for txn in history
        if window_start <= txn.timestamp < transaction.timestamp
    ]

    if len(recent_transactions) >= 2:

        return {
            "rule": "RAPID_FIRE",
            "transaction_count": len(recent_transactions) + 1,
            "window_minutes": 10
        }

    return None


def detect_new_location(
    transaction: TransactionSchema,
    history: list[TransactionSchema]
):
    """
    NEW_LOCATION rule:
    Flag when the current city has never previously
    appeared for this customer.

    The customer's first transaction must not
    automatically trigger this rule.
    """

    if not history:
        return None

    known_cities = {
        txn.city.strip().lower()
        for txn in history
    }

    current_city = transaction.city.strip().lower()

    if current_city not in known_cities:

        return {
            "rule": "NEW_LOCATION",
            "city": transaction.city,
            "known_cities": sorted({
                txn.city for txn in history
            })
        }

    return None


def detect_rules(
    transaction: TransactionSchema,
    history: list[TransactionSchema]
):
    """
    Run all four detection rules.

    Returns evidence for every triggered rule.
    """

    results = []

    high_amount_result = detect_high_amount(
        transaction,
        history
    )

    if high_amount_result:
        results.append(high_amount_result)


    night_result = detect_night_transaction(
        transaction
    )

    if night_result:
        results.append(night_result)


    rapid_fire_result = detect_rapid_fire(
        transaction,
        history
    )

    if rapid_fire_result:
        results.append(rapid_fire_result)


    new_location_result = detect_new_location(
        transaction,
        history
    )

    if new_location_result:
        results.append(new_location_result)

    return results


def evaluate_transaction(
    transaction: TransactionSchema,
    history: list[TransactionSchema]
):
    """
    Complete evaluation of one transaction.

    Steps:
    1. Run detection rules
    2. Extract triggered rule IDs
    3. Calculate risk score
    4. Determine risk level
    5. Generate explanation
    """

    rule_results = detect_rules(
        transaction,
        history
    )

    triggered_rules = [
        result["rule"]
        for result in rule_results
    ]

    risk_score = calculate_risk_score(
        triggered_rules
    )

    # No rule fired -> transaction is not flagged
    if risk_score == 0:

        return {
            "triggered_rules": [],
            "risk_score": 0,
            "risk_level": None,
            "explanation": ""
        }

    risk_level = get_risk_level(
        risk_score
    )

    explanation = generate_explanation(
        transaction,
        rule_results
    )

    return {
        "triggered_rules": triggered_rules,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "explanation": explanation
    }