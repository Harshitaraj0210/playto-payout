import { useState, useEffect } from "react";
import axios from "axios";

const API = "http://localhost:8000/api/v1";

const formatPaise = (paise) => `₹${(paise / 100).toFixed(2)}`;

const statusColor = (status) => {
  const colors = {
    pending: "#f59e0b",
    processing: "#3b82f6",
    completed: "#10b981",
    failed: "#ef4444",
  };
  return colors[status] || "#6b7280";
};

export default function App() {
  const [merchants, setMerchants] = useState([]);
  const [selectedMerchant, setSelectedMerchant] = useState(null);
  const [merchantDetail, setMerchantDetail] = useState(null);
  const [payouts, setPayouts] = useState([]);
  const [amount, setAmount] = useState("");
  const [bankAccount, setBankAccount] = useState("");
  const [message, setMessage] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    axios.get(`${API}/merchants/`).then((res) => setMerchants(res.data));
  }, []);

  useEffect(() => {
    if (!selectedMerchant) return;
    fetchMerchantDetail();
    fetchPayouts();
    const interval = setInterval(() => {
      fetchMerchantDetail();
      fetchPayouts();
    }, 5000);
    return () => clearInterval(interval);
  }, [selectedMerchant]);

  const fetchMerchantDetail = () => {
    axios
      .get(`${API}/merchants/${selectedMerchant}/`)
      .then((res) => setMerchantDetail(res.data));
  };

  const fetchPayouts = () => {
    axios
      .get(`${API}/merchants/${selectedMerchant}/payouts/`)
      .then((res) => setPayouts(res.data));
  };

  const handlePayoutRequest = async () => {
    if (!amount || !bankAccount) {
      setMessage({ type: "error", text: "Please fill all fields" });
      return;
    }
    setLoading(true);
    setMessage(null);
    try {
      const idempotencyKey = crypto.randomUUID();
      await axios.post(
        `${API}/merchants/${selectedMerchant}/payouts/request/`,
        { amount_paise: parseInt(amount), bank_account_id: bankAccount },
        { headers: { "Idempotency-Key": idempotencyKey } }
      );
      setMessage({ type: "success", text: "Payout requested successfully!" });
      setAmount("");
      setBankAccount("");
      fetchMerchantDetail();
      fetchPayouts();
    } catch (err) {
      setMessage({
        type: "error",
        text: err.response?.data?.error || "Request failed",
      });
    }
    setLoading(false);
  };

  return (
    <div style={{ fontFamily: "sans-serif", maxWidth: 900, margin: "0 auto", padding: 24 }}>
      <h1 style={{ color: "#1e293b", borderBottom: "2px solid #e2e8f0", paddingBottom: 12 }}>
        💳 Playto Pay — Merchant Dashboard
      </h1>

      {/* Merchant Selector */}
      <div style={{ marginBottom: 24 }}>
        <label style={{ fontWeight: 600 }}>Select Merchant: </label>
        <select
          onChange={(e) => setSelectedMerchant(e.target.value)}
          style={{ padding: "8px 12px", marginLeft: 8, borderRadius: 6, border: "1px solid #cbd5e1" }}
        >
          <option value="">-- Choose --</option>
          {merchants.map((m) => (
            <option key={m.id} value={m.id}>
              {m.name}
            </option>
          ))}
        </select>
      </div>

      {merchantDetail && (
        <>
          {/* Balance Cards */}
          <div style={{ display: "flex", gap: 16, marginBottom: 24 }}>
            <div style={{ flex: 1, background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: 8, padding: 20 }}>
              <div style={{ color: "#16a34a", fontSize: 13, fontWeight: 600 }}>AVAILABLE BALANCE</div>
              <div style={{ fontSize: 28, fontWeight: 700, color: "#15803d" }}>
                {formatPaise(merchantDetail.available_balance)}
              </div>
            </div>
            <div style={{ flex: 1, background: "#fffbeb", border: "1px solid #fde68a", borderRadius: 8, padding: 20 }}>
              <div style={{ color: "#d97706", fontSize: 13, fontWeight: 600 }}>HELD BALANCE</div>
              <div style={{ fontSize: 28, fontWeight: 700, color: "#b45309" }}>
                {formatPaise(merchantDetail.held_balance)}
              </div>
            </div>
            <div style={{ flex: 1, background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 8, padding: 20 }}>
              <div style={{ color: "#64748b", fontSize: 13, fontWeight: 600 }}>MERCHANT</div>
              <div style={{ fontSize: 18, fontWeight: 700, color: "#1e293b" }}>{merchantDetail.name}</div>
              <div style={{ fontSize: 12, color: "#94a3b8" }}>{merchantDetail.email}</div>
            </div>
          </div>

          {/* Payout Request Form */}
          <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 8, padding: 20, marginBottom: 24 }}>
            <h3 style={{ margin: "0 0 16px", color: "#1e293b" }}>Request Payout</h3>
            {message && (
              <div style={{
                padding: "10px 14px", borderRadius: 6, marginBottom: 12,
                background: message.type === "success" ? "#f0fdf4" : "#fef2f2",
                color: message.type === "success" ? "#16a34a" : "#dc2626",
                border: `1px solid ${message.type === "success" ? "#bbf7d0" : "#fecaca"}`
              }}>
                {message.text}
              </div>
            )}
            <div style={{ display: "flex", gap: 12, alignItems: "flex-end" }}>
              <div>
                <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Amount (paise)</div>
                <input
                  type="number"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder="e.g. 50000 = ₹500"
                  style={{ padding: "8px 12px", borderRadius: 6, border: "1px solid #cbd5e1", width: 180 }}
                />
              </div>
              <div>
                <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Bank Account</div>
                <input
                  type="text"
                  value={bankAccount}
                  onChange={(e) => setBankAccount(e.target.value)}
                  placeholder="e.g. HDFC0001234"
                  style={{ padding: "8px 12px", borderRadius: 6, border: "1px solid #cbd5e1", width: 180 }}
                />
              </div>
              <button
                onClick={handlePayoutRequest}
                disabled={loading}
                style={{
                  padding: "9px 20px", background: loading ? "#94a3b8" : "#3b82f6",
                  color: "white", border: "none", borderRadius: 6,
                  cursor: loading ? "not-allowed" : "pointer", fontWeight: 600
                }}
              >
                {loading ? "Requesting..." : "Request Payout"}
              </button>
            </div>
          </div>

          {/* Recent Ledger Entries */}
          <div style={{ marginBottom: 24 }}>
            <h3 style={{ color: "#1e293b" }}>Recent Transactions</h3>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ background: "#f1f5f9" }}>
                  <th style={{ padding: "8px 12px", textAlign: "left", fontSize: 13 }}>Type</th>
                  <th style={{ padding: "8px 12px", textAlign: "left", fontSize: 13 }}>Amount</th>
                  <th style={{ padding: "8px 12px", textAlign: "left", fontSize: 13 }}>Description</th>
                  <th style={{ padding: "8px 12px", textAlign: "left", fontSize: 13 }}>Date</th>
                </tr>
              </thead>
              <tbody>
                {merchantDetail.recent_entries?.map((entry) => (
                  <tr key={entry.id} style={{ borderBottom: "1px solid #e2e8f0" }}>
                    <td style={{ padding: "8px 12px" }}>
                      <span style={{
                        padding: "2px 8px", borderRadius: 4, fontSize: 12, fontWeight: 600,
                        background: entry.entry_type === "credit" ? "#f0fdf4" : "#fef2f2",
                        color: entry.entry_type === "credit" ? "#16a34a" : "#dc2626"
                      }}>
                        {entry.entry_type.toUpperCase()}
                      </span>
                    </td>
                    <td style={{ padding: "8px 12px", fontWeight: 600 }}>
                      {formatPaise(Math.abs(entry.amount))}
                    </td>
                    <td style={{ padding: "8px 12px", color: "#64748b", fontSize: 13 }}>{entry.description}</td>
                    <td style={{ padding: "8px 12px", color: "#94a3b8", fontSize: 12 }}>
                      {new Date(entry.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Payout History */}
          <div>
            <h3 style={{ color: "#1e293b" }}>Payout History <span style={{ fontSize: 12, color: "#94a3b8" }}>(auto-refreshes every 5s)</span></h3>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ background: "#f1f5f9" }}>
                  <th style={{ padding: "8px 12px", textAlign: "left", fontSize: 13 }}>ID</th>
                  <th style={{ padding: "8px 12px", textAlign: "left", fontSize: 13 }}>Amount</th>
                  <th style={{ padding: "8px 12px", textAlign: "left", fontSize: 13 }}>Status</th>
                  <th style={{ padding: "8px 12px", textAlign: "left", fontSize: 13 }}>Date</th>
                </tr>
              </thead>
              <tbody>
                {payouts.map((p) => (
                  <tr key={p.id} style={{ borderBottom: "1px solid #e2e8f0" }}>
                    <td style={{ padding: "8px 12px", fontSize: 11, color: "#94a3b8", fontFamily: "monospace" }}>
                      {p.id.slice(0, 8)}...
                    </td>
                    <td style={{ padding: "8px 12px", fontWeight: 600 }}>{formatPaise(p.amount_paise)}</td>
                    <td style={{ padding: "8px 12px" }}>
                      <span style={{
                        padding: "2px 8px", borderRadius: 4, fontSize: 12, fontWeight: 600,
                        background: statusColor(p.status) + "20",
                        color: statusColor(p.status)
                      }}>
                        {p.status.toUpperCase()}
                      </span>
                    </td>
                    <td style={{ padding: "8px 12px", color: "#94a3b8", fontSize: 12 }}>
                      {new Date(p.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
                {payouts.length === 0 && (
                  <tr><td colSpan={4} style={{ padding: 20, textAlign: "center", color: "#94a3b8" }}>No payouts yet</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}