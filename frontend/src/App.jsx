import { useRef, useState, useEffect } from "react";
import "./App.css";
import { flaggedTransactions } from "./mockData";


function App() {
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState("");
  const fileInputRef = useRef(null);
  const [transactions, setTransactions] = useState([]);
  const [summary, setSummary] = useState(null);
  const [selectedTransaction, setSelectedTransaction] = useState(null);
  const [activePage, setActivePage] = useState("overview");

  const API_URL = "http://127.0.0.1:8001";

  const loadDashboardData = async () => {
    try {
      const [summaryResponse, flagsResponse] = await Promise.all([
        fetch(`${API_URL}/summary`),
        fetch(`${API_URL}/flags`),
      ]);

      if (!summaryResponse.ok || !flagsResponse.ok) {
        throw new Error("Failed to load dashboard data");
      }

      const summaryData = await summaryResponse.json();
      const flagsData = await flagsResponse.json();

      const normalizedFlags = flagsData.map((flag) => ({
        id: flag.id,
        txnId: flag.txn_id,
        customerId: flag.customer_id,
        amount: flag.amount,
        timestamp: flag.timestamp,
        city: flag.city,
        beneficiaryId: flag.beneficiary_id,
        channel: flag.channel,
        riskScore: flag.risk_score,
        riskLevel: flag.risk_level,
        triggeredRules: flag.triggered_rules,
        explanation: flag.explanation,
        status: flag.status,
      }));

      setSummary(summaryData);
      setTransactions(normalizedFlags);
    } catch (error) {
      console.error("Failed to load dashboard data:", error);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  const handleAction = async (action) => {
    if (!selectedTransaction) return;

    try {
      const response = await fetch(
        `${API_URL}/flags/${selectedTransaction.id}`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            action,
            notes: "",
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to update transaction");
      }

      await loadDashboardData();

      setSelectedTransaction((current) => ({
        ...current,
        status: action,
      }));
    } catch (error) {
      console.error("Failed to update transaction:", error);
      alert(error.message || "Failed to update transaction");
    }
  };

  const handleUpload = async (event) => {
    const file = event.target.files?.[0];

    if (!file) return;

    setUploading(true);
    setUploadMessage("");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch("http://127.0.0.1:8001/upload", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

        if (!response.ok) {
          throw new Error(data.detail || "Upload failed");
        }

        setUploadMessage(
          `${data.uploaded_count} transactions processed • ${data.flagged_count} flagged`
        );
        await loadDashboardData();

      } catch (error) {
        setUploadMessage(error.message || "Upload failed");
      } finally {
        setUploading(false);
        event.target.value = "";
      }
    };

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">F</div>
          <div>
            <div className="brand-name">FraudLens</div>
            <div className="brand-subtitle">Risk Intelligence</div>
          </div>
        </div>

        <nav className="nav">
          <button
            className={`nav-item ${activePage === "overview" ? "active" : ""}`}
            onClick={() => setActivePage("overview")}
          >
            <span>◈</span>
            Overview
          </button>

          <button
            className={`nav-item ${activePage === "transactions" ? "active" : ""}`}
            onClick={() => setActivePage("transactions")}
          >
            <span>▣</span>
            Transactions
          </button>

          <button
            className={`nav-item ${activePage === "alerts" ? "active" : ""}`}
            onClick={() => setActivePage("alerts")}
          >
            <span>⚠</span>
            Alerts
          </button>
        </nav>

        <div className="sidebar-bottom">
          <button className="nav-item">
            <span>⚙</span>
            Settings
          </button>

          <div className="analyst">
            <div className="avatar">RA</div>
            <div>
              <div className="analyst-name">Reshma Analyst</div>
              <div className="analyst-role">Fraud Operations</div>
            </div>
          </div>
        </div>
      </aside>

      <main className="main-content">
        
        {activePage === "overview" && (
          <>
            <header className="topbar">
          <div>
            <div className="breadcrumb">Workspace / Overview</div>
            <h1>Fraud Detection Overview</h1>
            <p>Monitor suspicious transactions and investigate risk signals.</p>
          </div>

        <button
          className="upload-button"
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
        >
          {uploading ? "Uploading..." : "Upload CSV"}
        </button>

        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,text/csv"
          onChange={handleUpload}
          style={{ display: "none" }}
        />

        {uploadMessage && (
          <div className="upload-message">
            {uploadMessage}
          </div>
        )}
        </header>

        <section className="stats-grid">
          <div className="stat-card">
            <span className="stat-label">Total Transactions</span>
            <strong>{(summary?.total_transactions ?? 0).toLocaleString()}</strong>
            <span className="stat-meta">Processed</span>
          </div>

          <div className="stat-card">
            <span className="stat-label">Flagged Transactions</span>
            <strong>{summary?.total_flagged ?? 0}</strong>
            <span className="stat-meta">7.2% of total</span>
          </div>

          <div className="stat-card">
            <span className="stat-label">High Risk</span>
            <strong>{summary?.risk_breakdown?.High ?? 0}</strong>
            <span className="stat-meta">Requires attention</span>
          </div>

          <div className="stat-card">
            <span className="stat-label">Pending Review</span>
            <strong>
              {transactions.filter((transaction) => transaction.status === "Pending").length}
            </strong>
            <span className="stat-meta">Analyst queue</span>
          </div>
        </section>

        <section className="content-grid">
          <div className="panel">
            <div className="panel-header">
              <div>
                <h2>Risk Overview</h2>
                <p>Current distribution of flagged transactions.</p>
              </div>
            </div>

            <div className="risk-bars">
              <div className="risk-row">
                <div className="risk-info">
                  <span>High</span>
                  <strong>{summary?.risk_breakdown?.High ?? 0}</strong>
                </div>
                <div className="bar">
                  <div className="bar-fill high" style={{
                                                          width: `${
                                                            summary?.total_flagged
                                                              ? ((summary?.risk_breakdown?.High ?? 0) / summary.total_flagged) * 100
                                                              : 0
                                                          }%`,
                                                        }} />
                </div>
              </div>

              <div className="risk-row">
                <div className="risk-info">
                  <span>Medium</span>
                  <strong>{summary?.risk_breakdown?.Medium ?? 0}</strong>
                </div>
                <div className="bar">
                  <div className="bar-fill medium" style={{
  width: `${
    summary?.total_flagged
      ? ((summary?.risk_breakdown?.Medium ?? 0) / summary.total_flagged) * 100
      : 0
  }%`,
}} />
                </div>
              </div>

              <div className="risk-row">
                <div className="risk-info">
                  <span>Low</span>
                  <strong>{summary?.risk_breakdown?.Low ?? 0}</strong>
                </div>
                <div className="bar">
                  <div className="bar-fill low" style={{
  width: `${
    summary?.total_flagged
      ? ((summary?.risk_breakdown?.Low ?? 0) / summary.total_flagged) * 100
      : 0
  }%`,
}} />
                </div>
              </div>
            </div>
          </div>

          <div className="panel">
            <div className="panel-header">
              <div>
                <h2>Detection Rules</h2>
                <p>Signals contributing to flagged activity.</p>
              </div>
            </div>

            <div className="rule-list">
              <div className="rule">
                <span className="rule-dot" />
                <span>High Amount</span>
                <strong>{summary?.rule_breakdown?.HIGH_AMOUNT ?? 0}</strong>
              </div>

              <div className="rule">
                <span className="rule-dot" />
                <span>Night Transaction</span>
                <strong>{summary?.rule_breakdown?.NIGHT_TRANSACTION ?? 0}</strong>
              </div>

              <div className="rule">
                <span className="rule-dot" />
                <span>Rapid Fire</span>
                <strong>{summary?.rule_breakdown?.RAPID_FIRE ?? 0}</strong>
              </div>

              <div className="rule">
                <span className="rule-dot" />
                <span>New Location</span>
                <strong>{summary?.rule_breakdown?.NEW_LOCATION ?? 0}</strong>
              </div>
            </div>
          </div>
        </section>

        <section className="panel transactions-panel">
          <div className="panel-header">
            <div>
              <h2>Flagged Transactions</h2>
              <p>Transactions requiring analyst review.</p>
            </div>

            <button className="view-all">View all →</button>
          </div>

          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Transaction</th>
                  <th>Customer</th>
                  <th>Amount</th>
                  <th>Risk</th>
                  <th>Signals</th>
                  <th>Status</th>
                </tr>
              </thead>

              <tbody>
                {transactions.map((transaction) => (
                  <tr
                    key={transaction.id}
                    onClick={() => setSelectedTransaction(transaction)}
                    className="transaction-row"
                  >
                    <td className="transaction-id">
                      {transaction.txnId}
                    </td>

                    <td>{transaction.customerId}</td>

                    <td>
                      ₹{transaction.amount.toLocaleString("en-IN")}
                    </td>

                    <td>
                      <span
                        className={`risk-badge ${
                          transaction.riskLevel === "High"
                            ? "high-badge"
                            : transaction.riskLevel === "Medium"
                              ? "medium-badge"
                              : "low-badge"
                        }`}
                      >
                        {transaction.riskScore} · {transaction.riskLevel}
                      </span>
                    </td>

                    <td>
                      {transaction.triggeredRules
                        .map((rule) => rule.replaceAll("_", " "))
                        .join(" · ")}
                    </td>

                    <td>
                      <span
                        className={`status ${
                          transaction.status === "Pending"
                            ? "pending"
                            : "reviewed"
                        }`}
                      >
                        {transaction.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

          {selectedTransaction && (
            <section className="panel investigation-panel">
              <div className="panel-header">
                <div>
                  <h2>Transaction Investigation</h2>
                  <p>Analyst review for {selectedTransaction.txnId}</p>
                </div>

                <button
                  className="close-button"
                  onClick={() => setSelectedTransaction(null)}
                >
                  Close
                </button>
              </div>

              <div className="investigation-grid">
                <div className="investigation-item">
                  <span>Transaction</span>
                  <strong>{selectedTransaction.txnId}</strong>
                </div>

                <div className="investigation-item">
                  <span>Customer</span>
                  <strong>{selectedTransaction.customerId}</strong>
                </div>

                <div className="investigation-item">
                  <span>Amount</span>
                  <strong>
                    ₹{selectedTransaction.amount.toLocaleString("en-IN")}
                  </strong>
                </div>

                <div className="investigation-item">
                  <span>Risk Score</span>
                  <strong>
                    {selectedTransaction.riskScore} ·{" "}
                    {selectedTransaction.riskLevel}
                  </strong>
                </div>
              </div>

              <div className="investigation-section">
                <h3>Triggered Signals</h3>

                <div className="signal-list">
                  {selectedTransaction.triggeredRules.map((rule) => (
                    <span className="signal-tag" key={rule}>
                      {rule.replaceAll("_", " ")}
                    </span>
                  ))}
                </div>
              </div>

              <div className="investigation-section">
                <h3>Why was this flagged?</h3>

                <p className="explanation">
                  {selectedTransaction.explanation}
                </p>
              </div>

              <div className="investigation-actions">
                <button
                  className="action-button fraud"
                  onClick={() => handleAction("Fraud")}
                >
                  Mark Fraud
                </button>

                <button
                  className="action-button genuine"
                  onClick={() => handleAction("Genuine")}
                >
                  Mark Genuine
                </button>

                <button
                  className="action-button escalate"
                  onClick={() => handleAction("Escalate")}
                >
                  Escalate
                </button>
              </div>
            </section>
          )}
        </>
      )}

      {activePage === "transactions" && (
        <>
          <header className="topbar">
            <div>
              <div className="breadcrumb">Workspace / Transactions</div>
              <h1>Transactions</h1>
              <p>Review and investigate flagged transactions.</p>
            </div>

            <button
              className="view-all"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
            >
              {uploading ? "Uploading..." : "+ Upload CSV"}
            </button>
          </header>

          <section className="panel transactions-panel">
            <div className="panel-header">
              <div>
                <h2>All Flagged Transactions</h2>
                <p>Transactions identified by the detection engine.</p>
              </div>
            </div>

            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Transaction</th>
                    <th>Customer</th>
                    <th>Amount</th>
                    <th>Risk</th>
                    <th>Signals</th>
                    <th>Status</th>
                  </tr>
                </thead>

                <tbody>
                  {transactions.map((transaction) => (
                    <tr
                      key={transaction.id}
                      onClick={() => setSelectedTransaction(transaction)}
                      className="transaction-row"
                    >
                      <td className="transaction-id">
                        {transaction.txnId}
                      </td>

                      <td>{transaction.customerId}</td>

                      <td>
                        ₹{transaction.amount.toLocaleString("en-IN")}
                      </td>

                      <td>
                        <span
                          className={`risk-badge ${
                            transaction.riskLevel === "High"
                              ? "high-badge"
                              : transaction.riskLevel === "Medium"
                                ? "medium-badge"
                                : "low-badge"
                          }`}
                        >
                          {transaction.riskScore} · {transaction.riskLevel}
                        </span>
                      </td>

                      <td>
                        {transaction.triggeredRules
                          .map((rule) => rule.replaceAll("_", " "))
                          .join(" · ")}
                      </td>

                      <td>
                        <span
                          className={`status ${
                            transaction.status === "Pending"
                              ? "pending"
                              : "reviewed"
                          }`}
                        >
                          {transaction.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {selectedTransaction && (
            <section className="panel investigation-panel">
              <div className="panel-header">
                <div>
                  <h2>Transaction Investigation</h2>
                  <p>
                    Analyst review for {selectedTransaction.txnId}
                  </p>
                </div>

                <button
                  className="close-button"
                  onClick={() => setSelectedTransaction(null)}
                >
                  Close
                </button>
              </div>

              <div className="investigation-grid">
                <div className="investigation-item">
                  <span>Transaction</span>
                  <strong>{selectedTransaction.txnId}</strong>
                </div>

                <div className="investigation-item">
                  <span>Customer</span>
                  <strong>{selectedTransaction.customerId}</strong>
                </div>

                <div className="investigation-item">
                  <span>Amount</span>
                  <strong>
                    ₹{selectedTransaction.amount.toLocaleString("en-IN")}
                  </strong>
                </div>

                <div className="investigation-item">
                  <span>Risk Score</span>
                  <strong>
                    {selectedTransaction.riskScore} ·{" "}
                    {selectedTransaction.riskLevel}
                  </strong>
                </div>
              </div>

              <div className="investigation-section">
                <h3>Triggered Signals</h3>

                <div className="signal-list">
                  {selectedTransaction.triggeredRules.map((rule) => (
                    <span className="signal-tag" key={rule}>
                      {rule.replaceAll("_", " ")}
                    </span>
                  ))}
                </div>
              </div>

              <div className="investigation-section">
                <h3>Why was this flagged?</h3>

                <p className="explanation">
                  {selectedTransaction.explanation}
                </p>
              </div>

              <div className="investigation-actions">
                <button
                  className="action-button fraud"
                  onClick={() => handleAction("Fraud")}
                >
                  Mark Fraud
                </button>

                <button
                  className="action-button genuine"
                  onClick={() => handleAction("Genuine")}
                >
                  Mark Genuine
                </button>

                <button
                  className="action-button escalate"
                  onClick={() => handleAction("Escalate")}
                >
                  Escalate
                </button>
              </div>
            </section>
          )}
        </>
      )}

      {activePage === "alerts" && (
        <>
          <header className="topbar">
            <div>
              <div className="breadcrumb">Workspace / Alerts</div>
              <h1>Alerts</h1>
              <p>Prioritize suspicious activity requiring analyst attention.</p>
            </div>
          </header>

          <section className="stats-grid">
            <div className="stat-card">
              <span className="stat-label">Open Alerts</span>
              <strong>{summary?.total_flagged - transactions.filter(
                                                  (transaction) => transaction.status === "Pending"
                                                ).length}</strong>
              <span className="stat-meta">Awaiting review</span>
            </div>

            <div className="stat-card">
              <span className="stat-label">High Risk</span>
              <strong>{summary?.risk_breakdown?.High ?? 0}</strong>
              <span className="stat-meta">Priority alerts</span>
            </div>

            <div className="stat-card">
              <span className="stat-label">Medium Risk</span>
              <strong>{summary?.risk_breakdown?.Medium ?? 0}</strong>
              <span className="stat-meta">Requires review</span>
            </div>

            <div className="stat-card">
              <span className="stat-label">Low Risk</span>
              <strong>{summary?.risk_breakdown?.Low ?? 0}</strong>
              <span className="stat-meta">Lower priority</span>
            </div>
          </section>

          <section className="panel transactions-panel">
            <div className="panel-header">
              <div>
                <h2>Priority Alerts</h2>
                <p>Highest-risk transactions requiring analyst attention.</p>
              </div>
            </div>

            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Alert</th>
                    <th>Customer</th>
                    <th>Risk</th>
                    <th>Signals</th>
                    <th>Status</th>
                  </tr>
                </thead>

                <tbody>
                  {[...transactions]
                      .filter((transaction) => transaction.status === "Pending")
                      .sort((a, b) => b.riskScore - a.riskScore)
                    .map((transaction) => (
                      <tr
                        key={transaction.id}
                        onClick={() => setSelectedTransaction(transaction)}
                        className="transaction-row"
                      >
                        <td className="transaction-id">
                          {transaction.txnId}
                        </td>

                        <td>{transaction.customerId}</td>

                        <td>
                          <span
                            className={`risk-badge ${
                              transaction.riskLevel === "High"
                                ? "high-badge"
                                : transaction.riskLevel === "Medium"
                                  ? "medium-badge"
                                  : "low-badge"
                            }`}
                          >
                            {transaction.riskScore} · {transaction.riskLevel}
                          </span>
                        </td>

                        <td>
                          {transaction.triggeredRules
                            .map((rule) => rule.replaceAll("_", " "))
                            .join(" · ")}
                        </td>

                        <td>
                          <span
                            className={`status ${
                              transaction.status === "Pending"
                                ? "pending"
                                : "reviewed"
                            }`}
                          >
                            {transaction.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </section>

          {selectedTransaction && (
            <section className="panel investigation-panel">
              <div className="panel-header">
                <div>
                  <h2>Alert Investigation</h2>
                  <p>
                    Analyst review for {selectedTransaction.txnId}
                  </p>
                </div>

                <button
                  className="close-button"
                  onClick={() => setSelectedTransaction(null)}
                >
                  Close
                </button>
              </div>

              <div className="investigation-grid">
                <div className="investigation-item">
                  <span>Transaction</span>
                  <strong>{selectedTransaction.txnId}</strong>
                </div>

                <div className="investigation-item">
                  <span>Customer</span>
                  <strong>{selectedTransaction.customerId}</strong>
                </div>

                <div className="investigation-item">
                  <span>Amount</span>
                  <strong>
                    ₹{selectedTransaction.amount.toLocaleString("en-IN")}
                  </strong>
                </div>

                <div className="investigation-item">
                  <span>Risk Score</span>
                  <strong>
                    {selectedTransaction.riskScore} ·{" "}
                    {selectedTransaction.riskLevel}
                  </strong>
                </div>
              </div>

              <div className="investigation-section">
                <h3>Why was this flagged?</h3>

                <p className="explanation">
                  {selectedTransaction.explanation}
                </p>
              </div>

              <div className="investigation-actions">
                <button
                  className="action-button fraud"
                  onClick={() => handleAction("Fraud")}
                >
                  Mark Fraud
                </button>

                <button
                  className="action-button genuine"
                  onClick={() => handleAction("Genuine")}
                >
                  Mark Genuine
                </button>

                <button
                  className="action-button escalate"
                  onClick={() => handleAction("Escalate")}
                >
                  Escalate
                </button>
              </div>
            </section>
          )}
        </>
      )}
      </main>
    </div>
  );
}

export default App;