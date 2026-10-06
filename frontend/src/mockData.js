export const summaryData = {
  totalTransactions: 1040,
  totalFlagged: 75,
  highRisk: 12,
  pendingReview: 68,

  riskDistribution: {
    high: 12,
    medium: 41,
    low: 22,
  },

  ruleBreakdown: {
    HIGH_AMOUNT: 20,
    NIGHT_TRANSACTION: 30,
    RAPID_FIRE: 15,
    NEW_LOCATION: 25,
  },
};

export const flaggedTransactions = [
  {
    id: 1,
    txnId: "F0001",
    customerId: "C012",
    amount: 120000,
    riskScore: 85,
    riskLevel: "High",
    triggeredRules: ["HIGH_AMOUNT", "NIGHT_TRANSACTION"],
    explanation:
      "Amount exceeds the customer's usual spending and the transaction occurred at 2:14 AM.",
    status: "Pending",
  },

  {
    id: 2,
    txnId: "F0017",
    customerId: "C087",
    amount: 48500,
    riskScore: 60,
    riskLevel: "High",
    triggeredRules: ["RAPID_FIRE", "NEW_LOCATION"],
    explanation:
      "Multiple transactions occurred within a short period and the transaction originated from a new location.",
    status: "Pending",
  },

  {
    id: 3,
    txnId: "F0024",
    customerId: "C031",
    amount: 26800,
    riskScore: 50,
    riskLevel: "Medium",
    triggeredRules: ["NEW_LOCATION"],
    explanation:
      "The transaction occurred in a city not previously associated with this customer.",
    status: "Reviewed",
  },

  {
    id: 4,
    txnId: "F0031",
    customerId: "C044",
    amount: 95000,
    riskScore: 75,
    riskLevel: "High",
    triggeredRules: ["HIGH_AMOUNT", "RAPID_FIRE"],
    explanation:
      "The transaction amount is significantly higher than historical spending and multiple transactions occurred within 10 minutes.",
    status: "Pending",
  },

  {
    id: 5,
    txnId: "F0042",
    customerId: "C102",
    amount: 18400,
    riskScore: 25,
    riskLevel: "Low",
    triggeredRules: ["NIGHT_TRANSACTION"],
    explanation:
      "The transaction occurred between midnight and 5 AM.",
    status: "Pending",
  },
];