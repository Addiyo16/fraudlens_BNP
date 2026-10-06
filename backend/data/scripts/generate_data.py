import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)

# ============================================================
# CONFIG
# ============================================================

NORMAL_COUNT = 1000
ANOMALY_COUNT = 40

CUSTOMERS = [f"C{i:03d}" for i in range(1, 101)]

CITIES = [
    "Pune",
    "Mumbai",
    "Delhi",
    "Bangalore",
    "Hyderabad",
    "Chennai",
    "Kolkata",
    "Ahmedabad",
    "Jaipur",
    "Nagpur"
]

CHANNELS = [
    "UPI",
    "ATM",
    "NEFT",
    "IMPS"
]

BASE_TIME = datetime(2026, 1, 1, 8, 0)

ROOT_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = ROOT_DIR / "data"

DATA_DIR.mkdir(exist_ok=True)

OUTPUT_FILE = DATA_DIR / "transactions.csv"


transactions = []


# ============================================================
# 1. NORMAL TRANSACTIONS
# ============================================================

for i in range(NORMAL_COUNT):

    customer = random.choice(CUSTOMERS)

    transaction = {
        "txn_id": f"T{i + 1:04d}",
        "customer_id": customer,
        "amount": round(random.uniform(200, 5000), 2),
        "timestamp": BASE_TIME + timedelta(
            minutes=random.randint(0, 60 * 24 * 180)
        ),
        "city": random.choice(CITIES),
        "beneficiary_id": f"B{random.randint(1, 300):03d}",
        "channel": random.choice(CHANNELS)
    }

    transactions.append(transaction)


# ============================================================
# 2. HIGH AMOUNT — 10 anomalies
# ============================================================

for i in range(10):

    customer = f"C{i + 1:03d}"

    # Give the customer some normal transaction history
    history_time = BASE_TIME + timedelta(
        days=100 + i
    )

    transactions.append({
        "txn_id": f"T{1001 + i:04d}",
        "customer_id": customer,
        "amount": 1000.00,
        "timestamp": history_time,
        "city": "Pune",
        "beneficiary_id": "B001",
        "channel": "UPI"
    })

    # Large transaction
    transactions.append({
        "txn_id": f"A{i + 1:03d}",
        "customer_id": customer,
        "amount": 10000.00,
        "timestamp": history_time + timedelta(minutes=5),
        "city": "Pune",
        "beneficiary_id": "B002",
        "channel": "UPI"
    })


# ============================================================
# 3. NIGHT TRANSACTION — 10 anomalies
# ============================================================

for i in range(10):

    customer = f"C{20 + i:03d}"

    transactions.append({
        "txn_id": f"N{i + 1:03d}",
        "customer_id": customer,
        "amount": random.randint(1000, 5000),
        "timestamp": datetime(
            2026,
            7,
            1 + i,
            2,
            15
        ),
        "city": "Mumbai",
        "beneficiary_id": "B050",
        "channel": "UPI"
    })


# ============================================================
# 4. NEW LOCATION — 10 anomalies
# ============================================================

for i in range(10):

    customer = f"C{40 + i:03d}"

    known_city = "Pune"

    new_city = CITIES[
        (CITIES.index(known_city) + i + 1)
        % len(CITIES)
    ]

    base_time = datetime(
        2026,
        7,
        15 + (i % 10),
        10,
        0
    )

    # Previous known location
    transactions.append({
        "txn_id": f"LH{i + 1:03d}",
        "customer_id": customer,
        "amount": 1500,
        "timestamp": base_time - timedelta(days=2),
        "city": known_city,
        "beneficiary_id": "B100",
        "channel": "UPI"
    })

    # New location
    transactions.append({
        "txn_id": f"LN{i + 1:03d}",
        "customer_id": customer,
        "amount": 1500,
        "timestamp": base_time,
        "city": new_city,
        "beneficiary_id": "B101",
        "channel": "UPI"
    })


# ============================================================
# 5. RAPID FIRE — 10 anomalies
# ============================================================

for i in range(10):

    customer = f"C{60 + i:03d}"

    base_time = datetime(
        2026,
        8,
        1 + i,
        14,
        0
    )

    for j in range(3):

        transactions.append({
            "txn_id": f"RF{i + 1:02d}_{j + 1}",
            "customer_id": customer,
            "amount": 1200 + (j * 100),
            "timestamp": base_time + timedelta(
                minutes=j * 2
            ),
            "city": "Pune",
            "beneficiary_id": f"B{200 + j:03d}",
            "channel": "UPI"
        })


# ============================================================
# SORT CHRONOLOGICALLY
# ============================================================

transactions.sort(
    key=lambda x: x["timestamp"]
)


# ============================================================
# TAKE EXACTLY 1040
# ============================================================

# The anomaly construction intentionally creates supporting
# historical transactions. We select the first 1040 records
# after sorting, then report the actual count.

if len(transactions) != 1040:
    print(
        f"WARNING: Generated {len(transactions)} rows "
        f"instead of 1040."
    )


# ============================================================
# WRITE CSV
# ============================================================

with open(
    OUTPUT_FILE,
    "w",
    newline="",
    encoding="utf-8"
) as file:

    fieldnames = [
        "txn_id",
        "customer_id",
        "amount",
        "timestamp",
        "city",
        "beneficiary_id",
        "channel"
    ]

    writer = csv.DictWriter(
        file,
        fieldnames=fieldnames
    )

    writer.writeheader()

    for transaction in transactions:

        writer.writerow({
            "txn_id": transaction["txn_id"],
            "customer_id": transaction["customer_id"],
            "amount": transaction["amount"],
            "timestamp": transaction["timestamp"]
                .strftime("%Y-%m-%d %H:%M:%S"),
            "city": transaction["city"],
            "beneficiary_id": transaction["beneficiary_id"],
            "channel": transaction["channel"]
        })


print()
print("===================================")
print("FraudLens Dataset Generated")
print("===================================")
print(f"Total rows: {len(transactions)}")
print(f"Output: {OUTPUT_FILE}")
print("===================================")