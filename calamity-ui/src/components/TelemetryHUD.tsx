import React from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

interface TelemetryProps {
  telemetry: {
    math_engine: {
      affected_population: { val_rmse: number; val_mae: number; feature_importances: Record<string, number> };
      economic_damage: { val_rmse: number; val_mae: number; feature_importances: Record<string, number> };
    };
    rag_engine: { average_cosine_similarity: number };
  } | null;
}

export default function TelemetryHUD({ telemetry }: TelemetryProps) {
  if (!telemetry) return null;

  const rawFeatures = telemetry.math_engine?.affected_population?.feature_importances || {};
  const chartData = Object.entries(rawFeatures)
    .map(([name, value]) => ({ name, value: Number(value.toFixed(4)) }))
    .sort((a, b) => b.value - a.value);

  const rmse = telemetry.math_engine?.affected_population?.val_rmse?.toLocaleString() ?? "—";
  const mae  = telemetry.math_engine?.affected_population?.val_mae?.toLocaleString()  ?? "—";
  const sim  = telemetry.rag_engine?.average_cosine_similarity ?? 0;
  const simPct = Math.round(sim * 100);
  const simColor = sim > 0.8 ? "var(--green)" : sim > 0.6 ? "var(--amber)" : "var(--red)";

  return (
    <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "8px", overflow: "hidden" }}>
      <div style={{ padding: "16px 24px", borderBottom: "1px solid var(--border)" }}>
        <p style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-1)" }}>Model Diagnostics</p>
      </div>

      <div style={{ padding: "24px", display: "grid", gridTemplateColumns: "200px 1fr 200px", gap: "32px", alignItems: "start" }}>

        {/* Math Engine metrics */}
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <p style={{ fontSize: "10px", fontWeight: 500, color: "var(--text-2)", letterSpacing: "0.06em", textTransform: "uppercase" }}>Math Engine</p>
          <div>
            <p style={{ fontSize: "10px", color: "var(--text-2)", marginBottom: "4px" }}>RMSE — Affected Population</p>
            <p style={{ fontSize: "20px", fontWeight: 600, fontFamily: "var(--font-geist-mono)", color: "var(--text-1)", letterSpacing: "-0.02em" }}>{rmse}</p>
          </div>
          <div>
            <p style={{ fontSize: "10px", color: "var(--text-2)", marginBottom: "4px" }}>MAE — Affected Population</p>
            <p style={{ fontSize: "20px", fontWeight: 600, fontFamily: "var(--font-geist-mono)", color: "var(--text-1)", letterSpacing: "-0.02em" }}>{mae}</p>
          </div>
        </div>

        {/* Feature importance */}
        <div style={{ borderLeft: "1px solid var(--border)", paddingLeft: "32px", display: "flex", flexDirection: "column", gap: "12px" }}>
          <p style={{ fontSize: "10px", fontWeight: 500, color: "var(--text-2)", letterSpacing: "0.06em", textTransform: "uppercase" }}>Feature Importance</p>
          <div style={{ height: "140px" }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} layout="vertical" margin={{ top: 0, right: 0, left: 8, bottom: 0 }}>
                <XAxis type="number" hide />
                <YAxis dataKey="name" type="category" axisLine={false} tickLine={false} tick={{ fill: "var(--text-3)", fontSize: 10 }} width={76} />
                <Tooltip
                  cursor={{ fill: "rgba(255,255,255,0.02)" }}
                  contentStyle={{ background: "var(--surface-raised)", border: "1px solid var(--border)", borderRadius: "6px", fontSize: "11px" }}
                  itemStyle={{ color: "var(--text-1)" }}
                  labelStyle={{ color: "var(--text-2)" }}
                />
                <Bar dataKey="value" radius={[0, 3, 3, 0]}>
                  {chartData.map((_, i) => (
                    <Cell key={i} fill={i === 0 ? "var(--accent)" : "rgba(255,255,255,0.18)"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* RAG confidence */}
        <div style={{ borderLeft: "1px solid var(--border)", paddingLeft: "32px", display: "flex", flexDirection: "column", gap: "16px" }}>
          <p style={{ fontSize: "10px", fontWeight: 500, color: "var(--text-2)", letterSpacing: "0.06em", textTransform: "uppercase" }}>RAG Confidence</p>
          <div>
            <p style={{ fontSize: "32px", fontWeight: 700, fontFamily: "var(--font-geist-mono)", color: simColor, letterSpacing: "-0.03em", marginBottom: "12px" }}>
              {simPct}%
            </p>
            <div style={{ height: "4px", borderRadius: "9999px", background: "var(--surface-raised)", border: "1px solid var(--border)", overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${simPct}%`, background: simColor, borderRadius: "9999px", transition: "width 0.8s ease" }} />
            </div>
          </div>
          <p style={{ fontSize: "11px", lineHeight: "1.6", color: "var(--text-3)", fontFamily: "var(--font-geist-mono)" }}>
            {sim > 0.8 ? "High alignment. Analogies are strongly relevant."
            : sim > 0.6 ? "Moderate alignment. Proceed carefully."
            : "Low confidence. Generalized physics mode."}
          </p>
        </div>

      </div>
    </div>
  );
}
