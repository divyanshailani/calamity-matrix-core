import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MapPin, Calendar, Sparkles } from "lucide-react";

interface HistoricalContextProps {
  results: any;
  country?: string;
  onSuggestionClick?: (updates: any) => void;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  onAskAI?: (ctx?: any) => void;
}

function scoreColor(s: number) {
  if (s >= 0.75) return "var(--green)";
  if (s >= 0.60) return "var(--amber)";
  return "var(--red)";
}

export default function HistoricalContext({ results, country, onSuggestionClick, onAskAI }: HistoricalContextProps) {
  return (
    <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "8px", display: "flex", flexDirection: "column", height: "100%", overflow: "hidden", backfaceVisibility: "hidden" }}>

      {/* Header */}
      <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0 }}>
        <div>
          <p style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-1)" }}>Historical Context</p>
          <span style={{ fontSize: "11px", color: "var(--text-2)", fontFamily: "var(--font-geist-mono)" }}>pgvector RAG</span>
        </div>
        <button
          onClick={() => onAskAI?.()}
          style={{
            padding: "6px 12px",
            background: "var(--accent)",
            border: "1px solid var(--border-hover)",
            borderRadius: "6px",
            color: "white",
            fontSize: "12px",
            fontWeight: 500,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "6px",
            transition: "all 0.2s"
          }}
        >
          Ask AI <Sparkles size={12} />
        </button>
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflowY: "auto", padding: "16px 20px", minHeight: 0 }}>
        <AnimatePresence mode="wait">
          {!results ? (
            <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              style={{ height: "100%", minHeight: "200px", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: "8px" }}>
              <p style={{ fontSize: "13px", color: "var(--text-2)" }}>No simulation active</p>
              <p style={{ fontSize: "11px", color: "var(--text-3)" }}>Run a simulation to retrieve analogies</p>
            </motion.div>
          ) : (
            <motion.div key="results" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>

              {results.historical_context.length === 0 ? (
                <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                  <div style={{ padding: "12px 14px", background: "var(--surface-raised)", border: "1px solid var(--border)", borderRadius: "6px" }}>
                    <p style={{ fontSize: "12px", color: "var(--amber)", fontWeight: 500, marginBottom: "4px" }}>No exact matches found</p>
                    <p style={{ fontSize: "11px", color: "var(--text-2)", lineHeight: "1.5" }}>
                      No historical records for this combination. Try an alternative below.
                    </p>
                  </div>

                  {results.suggested_alternatives?.same_country_disasters?.length > 0 && (
                    <div>
                      <p style={{ fontSize: "10px", fontWeight: 600, color: "var(--text-2)", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: "8px", display: "flex", alignItems: "center", gap: "4px" }}>
                        <MapPin size={10} /> Other hazards in {country}
                      </p>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                        {results.suggested_alternatives.same_country_disasters.map((d: string) => (
                          <button key={d} onClick={() => onSuggestionClick?.({ disaster_type: d })}
                            style={{ fontSize: "11px", padding: "4px 10px", background: "var(--surface-raised)", border: "1px solid var(--border)", borderRadius: "4px", color: "var(--text-2)", cursor: "pointer", fontFamily: "var(--font-sans)" }}>
                            {d}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {results.suggested_alternatives?.closest_historical_years?.length > 0 && (
                    <div>
                      <p style={{ fontSize: "10px", fontWeight: 600, color: "var(--text-2)", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: "8px", display: "flex", alignItems: "center", gap: "4px" }}>
                        <Calendar size={10} /> Nearest recorded years
                      </p>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                        {results.suggested_alternatives.closest_historical_years.map((y: number) => (
                          <button key={y} onClick={() => onSuggestionClick?.({ event_year: y })}
                            style={{ fontSize: "11px", padding: "4px 10px", background: "var(--surface-raised)", border: "1px solid var(--border)", borderRadius: "4px", color: "var(--text-2)", cursor: "pointer", fontFamily: "var(--font-geist-mono)" }}>
                            {y}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                results.historical_context.map((ctx: any, idx: number) => {
                  const color = scoreColor(ctx.similarity_score);
                  const pct = (ctx.similarity_score * 100).toFixed(0);
                  return (
                    <div key={idx} style={{
                      background: "var(--surface-raised)",
                      border: "1px solid var(--border)",
                      borderLeft: `2px solid ${color}`,
                      borderRadius: "6px",
                      padding: "12px 14px",
                    }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
                        <div>
                          <p style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-1)", marginBottom: "2px" }}>
                            {String(ctx.country).startsWith("http") ? "ReliefWeb" : String(ctx.country)}
                          </p>
                          <p style={{ fontSize: "10px", color: "var(--text-2)" }}>
                            {String(ctx.disaster_type).match(/^\d+$/) ? `ID: ${ctx.disaster_type}` : ctx.disaster_type}
                            {ctx.event_year ? ` · ${ctx.event_year}` : ""}
                          </p>
                        </div>
                      </div>
                      <p style={{ fontSize: "11px", lineHeight: "1.6", color: "var(--text-2)" }}>
                        {ctx.text_preview || ctx.narrative_preview}
                      </p>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "12px" }}>
                        <span style={{ fontSize: "10px", fontWeight: 600, fontFamily: "var(--font-geist-mono)", color, flexShrink: 0 }}>
                          {pct}%
                        </span>
                        <button
                          onClick={() => onAskAI?.(ctx)}
                          style={{
                            padding: "4px 8px",
                            background: "var(--bg)",
                            border: "1px solid var(--border-hover)",
                            borderRadius: "4px",
                            color: "var(--text-1)",
                            fontSize: "10px",
                            fontWeight: 500,
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            gap: "4px",
                            transition: "all 0.2s"
                          }}
                        >
                          Ask AI <Sparkles size={10} />
                        </button>
                      </div>
                    </div>
                  );
                })
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
