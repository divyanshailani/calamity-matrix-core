"use client";

import React, { useState, useEffect } from "react";
import axios from "axios";
import Header from "../../components/Header";
import SimulationConfig from "../../components/SimulationConfig";
import GeospatialMap from "../../components/GeospatialMap";
import HistoricalContext from "../../components/HistoricalContext";
import TelemetryHUD from "../../components/TelemetryHUD";
import { countryCoords } from "../../lib/constants";
import { motion, AnimatePresence } from "framer-motion";
import { X, Zap, Database, Activity } from "lucide-react";

// ─── Onboarding Modal ─────────────────────────────────────────
function OnboardingModal({ onDismiss }: { onDismiss: () => void }) {
  return (
    <div
      onClick={onDismiss}
      style={{
        position: "fixed", inset: 0, zIndex: 1000,
        background: "rgba(0,0,0,0.7)", backdropFilter: "blur(6px)",
        display: "flex", alignItems: "center", justifyContent: "center", padding: "24px",
      }}
    >
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 8 }}
        transition={{ duration: 0.25, ease: "easeOut" }}
        onClick={e => e.stopPropagation()}
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border-hover)",
          borderRadius: "12px",
          padding: "32px",
          maxWidth: "480px",
          width: "100%",
          position: "relative",
        }}
      >
        <button onClick={onDismiss} id="modal-close-btn"
          style={{ position: "absolute", top: "16px", right: "16px", background: "none", border: "none", cursor: "pointer", color: "var(--text-3)", display: "flex" }}>
          <X size={16} />
        </button>

        <h2 style={{ fontSize: "18px", fontWeight: 600, color: "var(--text-1)", letterSpacing: "-0.02em", marginBottom: "8px" }}>
          Welcome to Calamity AI
        </h2>
        <p style={{ fontSize: "13px", color: "var(--text-2)", lineHeight: "1.6", marginBottom: "28px" }}>
          A neuro-symbolic disaster intelligence engine. Here is how it works:
        </p>

        <div style={{ display: "flex", flexDirection: "column", gap: "16px", marginBottom: "32px" }}>
          {[
            { icon: <Zap size={14} />, title: "XGBoost Math Engine", desc: "Predicts affected population and economic impact using 25 years of fused multi-source disaster data." },
            { icon: <Database size={14} />, title: "pgvector RAG Memory", desc: "Semantic search over 2,281 historical situation reports embedded as 1024-dim vectors using BGE-Large." },
            { icon: <Activity size={14} />, title: "Neuro-Symbolic Fusion", desc: "Both engines run in parallel — numbers from ML, context from RAG, together in one interface." },
          ].map(f => (
            <div key={f.title} style={{ display: "flex", gap: "12px" }}>
              <div style={{ width: "28px", height: "28px", borderRadius: "6px", background: "var(--surface-raised)", border: "1px solid var(--border)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-2)", flexShrink: 0 }}>
                {f.icon}
              </div>
              <div>
                <p style={{ fontSize: "13px", fontWeight: 500, color: "var(--text-1)", marginBottom: "3px" }}>{f.title}</p>
                <p style={{ fontSize: "12px", color: "var(--text-2)", lineHeight: "1.55" }}>{f.desc}</p>
              </div>
            </div>
          ))}
        </div>

        <button
          id="modal-proceed-btn"
          onClick={onDismiss}
          style={{
            width: "100%", padding: "10px", background: "var(--accent)", color: "white",
            border: "none", borderRadius: "6px", fontSize: "13px", fontWeight: 500, cursor: "pointer",
            fontFamily: "var(--font-sans)",
          }}
        >
          Open Simulator
        </button>
        <p style={{ textAlign: "center", fontSize: "11px", color: "var(--text-3)", marginTop: "10px" }}>
          Won't show again after you dismiss.
        </p>
      </motion.div>
    </div>
  );
}

// ─── Dashboard ────────────────────────────────────────────────
export default function Dashboard() {
  const [mounted, setMounted] = useState(false);
  const [showModal, setShowModal] = useState(false);

  const [formData, setFormData] = useState({
    country: "USA", disaster_type: "Earthquake", month: 1,
    event_year: "2026", severity: 5.0,
    query_text: "A massive earthquake striking a populated urban area.",
  });
  const [viewState, setViewState] = useState({ latitude: 37.09, longitude: -95.71, zoom: 3 });
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [consoleLogs, setConsoleLogs] = useState(["System initialized.", "Ready for simulation."]);

  useEffect(() => {
    setMounted(true);
    if (!localStorage.getItem("calamity_seen_v1")) setShowModal(true);
  }, []);

  const dismiss = () => { localStorage.setItem("calamity_seen_v1", "1"); setShowModal(false); };
  const addLog = (m: string) => setConsoleLogs(p => [...p.slice(-4), `[${new Date().toLocaleTimeString()}] ${m}`]);

  const run = async (data: typeof formData) => {
    setIsLoading(true); setError(null); setResults(null);
    addLog(`Running ${data.disaster_type} · ${data.country}...`);
    const coords = countryCoords[data.country];
    if (coords) setViewState({ latitude: coords.lat, longitude: coords.lng, zoom: coords.zoom });
    try {
      const res = await axios.post(
        process.env.NODE_ENV === "production" 
          ? "https://calamity-matrix-orchestrator.onrender.com/api/v1/simulate_calamity"
          : "http://localhost:8000/api/v1/simulate_calamity", {
        query_text: data.query_text, country: data.country, disaster_type: data.disaster_type,
        month: Number(data.month), event_year: Number(data.event_year), severity: Number(data.severity),
      });
      setResults(res.data);
      addLog("Simulation complete.");
      if (coords) setViewState({ latitude: coords.lat, longitude: coords.lng, zoom: coords.zoom + 2 });
    } catch (e: any) {
      const msg = e.response?.data?.detail || e.message || "Connection failed.";
      setError(msg); addLog(`Error: ${msg}`);
    } finally { setIsLoading(false); }
  };

  const handleSubmit = (e: React.FormEvent) => { e.preventDefault(); run(formData); };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden", background: "var(--bg)" }}>
      <AnimatePresence>{showModal && <OnboardingModal onDismiss={dismiss} />}</AnimatePresence>
      <Header />

      <main style={{ flex: 1, display: "grid", gridTemplateColumns: "minmax(240px, 1fr) 2fr minmax(240px, 1fr)", gridTemplateRows: "1fr auto", gap: "12px", padding: "12px", overflow: "hidden", minHeight: 0 }}>

        {/* Config */}
        <div style={{ gridRow: "1", display: "flex", flexDirection: "column", minHeight: 0 }}>
          <SimulationConfig formData={formData} setFormData={setFormData} handleSubmit={handleSubmit}
            isLoading={isLoading} consoleLogs={consoleLogs} addLog={addLog} />
        </div>

        {/* Map */}
        <div style={{ gridRow: "1", display: "flex", flexDirection: "column", minHeight: 0 }}>
          {mounted && <GeospatialMap viewState={viewState} setViewState={setViewState} results={results} error={error} country={formData.country} />}
        </div>

        {/* RAG */}
        <div style={{ gridRow: "1", display: "flex", flexDirection: "column", minHeight: 0 }}>
          <HistoricalContext results={results} country={formData.country}
            onSuggestionClick={u => { const d = { ...formData, ...u }; setFormData(d); run(d); }} />
        </div>

        {/* Telemetry — bottom row */}
        <div style={{ gridColumn: "1 / -1", gridRow: "2" }}>
          <AnimatePresence>
            {results?.telemetry && (
              <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.3 }}>
                <TelemetryHUD telemetry={results.telemetry} />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}
