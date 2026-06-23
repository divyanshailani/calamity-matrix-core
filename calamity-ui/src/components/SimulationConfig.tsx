import React from "react";
import { getSeverityLabel, countries, disasters, months, defaultContexts } from "../lib/constants";

interface SimulationConfigProps {
  formData: any;
  setFormData: (data: any) => void;
  handleSubmit: (e: React.FormEvent) => void;
  isLoading: boolean;
  consoleLogs: string[];
  addLog: (msg: string) => void;
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <label style={{ display: "block", fontSize: "11px", fontWeight: 500, color: "var(--text-2)", marginBottom: "6px", letterSpacing: "0.04em" }}>
      {children}
    </label>
  );
}

export default function SimulationConfig({ formData, setFormData, handleSubmit, isLoading, consoleLogs }: SimulationConfigProps) {
  return (
    <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "8px", display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>

      {/* Header */}
      <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)" }}>
        <p style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-1)" }}>Simulation Config</p>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} style={{ padding: "20px", flex: 1, display: "flex", flexDirection: "column", gap: "16px", overflowY: "auto" }}>

        <div>
          <Label>Country</Label>
          <select
            className="form-select"
            value={formData.country}
            onChange={e => setFormData({ ...formData, country: e.target.value })}
          >
            {countries.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>

        <div>
          <Label>Hazard Type</Label>
          <select
            className="form-select"
            value={formData.disaster_type}
            onChange={e => {
              const t = e.target.value;
              setFormData({ ...formData, disaster_type: t, query_text: defaultContexts[t] });
            }}
          >
            {disasters.map(d => <option key={d} value={d}>{d}</option>)}
          </select>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
          <div>
            <Label>Month</Label>
            <select className="form-select" value={formData.month} onChange={e => setFormData({ ...formData, month: Number(e.target.value) })}>
              {months.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>
          <div>
            <Label>Year</Label>
            <input
              type="text"
              maxLength={4}
              className="form-input"
              style={{ fontFamily: "var(--font-geist-mono)" }}
              value={formData.event_year}
              onChange={e => {
                let v = e.target.value.replace(/\D/g, "");
                if (v.length === 4 && parseInt(v) > 2026) v = "2026";
                setFormData({ ...formData, event_year: v });
              }}
            />
          </div>
        </div>

        <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <Label>{getSeverityLabel(formData.disaster_type)}</Label>
            <span style={{ fontSize: "12px", fontFamily: "var(--font-geist-mono)", color: "var(--text-1)", background: "var(--surface-raised)", border: "1px solid var(--border)", borderRadius: "4px", padding: "2px 8px" }}>
              {formData.severity}
            </span>
          </div>
          <input
            type="range"
            min="1" max="10" step="0.1"
            className="range-input"
            value={formData.severity}
            onChange={e => setFormData({ ...formData, severity: Number(e.target.value) })}
          />
        </div>

        <div>
          <Label>Scenario Context</Label>
          <textarea
            className="form-input"
            style={{ resize: "none", height: "80px", lineHeight: "1.5" }}
            value={formData.query_text}
            onChange={e => setFormData({ ...formData, query_text: e.target.value })}
            placeholder="Describe the scenario..."
          />
        </div>

        <div style={{ marginTop: "auto" }}>
          <button
            id="run-simulation-btn"
            type="submit"
            disabled={isLoading}
            style={{
              width: "100%",
              padding: "10px",
              background: isLoading ? "var(--surface-raised)" : "var(--accent)",
              color: isLoading ? "var(--text-3)" : "white",
              border: "1px solid " + (isLoading ? "var(--border)" : "transparent"),
              borderRadius: "6px",
              fontSize: "13px",
              fontWeight: 500,
              cursor: isLoading ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "8px",
              transition: "background 0.15s ease",
              fontFamily: "var(--font-sans)",
            }}
          >
            {isLoading ? (
              <>
                <span style={{ width: "12px", height: "12px", border: "1.5px solid var(--text-3)", borderTopColor: "var(--text-2)", borderRadius: "50%", display: "inline-block", animation: "spin 0.7s linear infinite" }} />
                Running...
              </>
            ) : "Run Simulation"}
          </button>
        </div>
      </form>

      {/* Console */}
      <div style={{ padding: "12px 20px", borderTop: "1px solid var(--border)" }}>
        <div style={{
          background: "var(--bg)",
          border: "1px solid var(--border)",
          borderRadius: "6px",
          padding: "10px 12px",
          maxHeight: "64px",
          overflowY: "auto",
          fontFamily: "var(--font-geist-mono)",
          fontSize: "10px",
          color: "var(--text-2)",
          lineHeight: "1.6",
        }}>
          {consoleLogs.map((log, i) => <div key={i}>{log}</div>)}
        </div>
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
