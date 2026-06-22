"use client";

import React, { useState, useEffect } from "react";
import axios from "axios";
import { motion, AnimatePresence } from "framer-motion";
import { AlertTriangle, Activity, Database, Clock, MapPin, Search, ShieldAlert, Cpu, Terminal } from "lucide-react";
import Map, { NavigationControl, Marker } from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";

const countryCoords: Record<string, { lat: number; lng: number; zoom: number }> = {
  "USA": { lat: 37.0902, lng: -95.7129, zoom: 3 },
  "Indonesia": { lat: -0.7893, lng: 113.9213, zoom: 4 },
  "Japan": { lat: 36.2048, lng: 138.2529, zoom: 4.5 },
  "China": { lat: 35.8617, lng: 104.1954, zoom: 3 },
  "India": { lat: 20.5937, lng: 78.9629, zoom: 4 },
  "Philippines": { lat: 12.8797, lng: 121.7740, zoom: 5 },
  "Mexico": { lat: 23.6345, lng: -102.5528, zoom: 4 },
  "Turkey": { lat: 38.9637, lng: 35.2433, zoom: 5 },
  "Chile": { lat: -35.6751, lng: -71.5430, zoom: 4 },
};

export default function Dashboard() {
  const [isMounted, setIsMounted] = useState(false);
  const [formData, setFormData] = useState({
    country: "USA",
    disaster_type: "Earthquake",
    month: 1,
    event_year: "2026",
    severity: 5.0,
    query_text: "A massive earthquake striking a populated urban area.",
  });

  const [viewState, setViewState] = useState({
    latitude: 37.0902,
    longitude: -95.7129,
    zoom: 3
  });

  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [consoleLogs, setConsoleLogs] = useState<string[]>([
    "System Initialized.",
    "Ready for simulation."
  ]);

  const countries = ["USA", "Indonesia", "Japan", "China", "India", "Philippines", "Mexico", "Turkey", "Chile"];
  const disasters = ["Earthquake", "Flood", "Storm", "Wildfire", "Volcanic activity", "Drought", "Extreme temperature"];
  const months = Array.from({ length: 12 }, (_, i) => i + 1);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  const addLog = (msg: string) => {
    setConsoleLogs(prev => [...prev.slice(-3), `[${new Date().toLocaleTimeString()}] ${msg}`]);
  };

  const getSeverityLabel = (type: string) => {
    switch(type) {
      case "Earthquake": return "Magnitude (Richter Scale)";
      case "Flood": return "Severity (Water Depth/Area)";
      case "Storm": return "Severity (Category/Wind Speed)";
      case "Wildfire": return "Severity (Burn Area)";
      default: return "Severity / Magnitude";
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setResults(null);
    addLog(`Simulating ${formData.disaster_type} in ${formData.country}...`);

    const coords = countryCoords[formData.country];
    if (coords) {
      setViewState({
        latitude: coords.lat,
        longitude: coords.lng,
        zoom: coords.zoom
      });
    }

    try {
      const response = await axios.post("http://localhost:8000/api/v1/simulate_calamity", {
        query_text: formData.query_text,
        country: formData.country,
        disaster_type: formData.disaster_type,
        month: Number(formData.month),
        event_year: Number(formData.event_year),
        severity: Number(formData.severity),
      });
      setResults(response.data);
      addLog("Simulation completed successfully.");
      
      // Auto-zoom in when results load to focus on the 3 tactical points
      if (coords) {
        setViewState({
          latitude: coords.lat,
          longitude: coords.lng,
          zoom: coords.zoom + 2.5
        });
      }
    } catch (err: any) {
      console.error(err);
      const errMsg = err.response?.data?.detail || err.message || "Connection offline.";
      setError(errMsg);
      addLog(`Execution failed: ${errMsg}`);
    } finally {
      setIsLoading(false);
    }
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('en-US').format(Math.round(num));
  };

  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900 font-sans selection:bg-zinc-200 overflow-x-hidden flex flex-col">
      {/* HEADER */}
      <header className="bg-white border-b border-zinc-200 px-6 py-4 flex items-center justify-between sticky top-0 z-50 shadow-sm">
        <div className="flex items-center gap-3">
          <Activity className="w-5 h-5 text-zinc-900" />
          <h1 className="text-sm font-semibold tracking-wide text-zinc-900">
            Calamity AI
          </h1>
        </div>
        <div className="text-xs font-medium text-zinc-500 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          System Online
        </div>
      </header>

      {/* THREE-COLUMN LAYOUT */}
      <main className="p-6 mx-auto grid grid-cols-1 lg:grid-cols-12 gap-6 flex-grow w-full max-w-[1600px]">
        
        {/* COLUMN 1: CONFIGURATION (Span 3) */}
        <div className="lg:col-span-3 flex flex-col">
          <div className="bg-white border border-zinc-200 rounded-xl p-5 shadow-sm flex flex-col h-full">
            
            <div className="flex items-center gap-2 mb-6 pb-3 border-b border-zinc-100">
              <Cpu className="w-4 h-4 text-zinc-400" />
              <h2 className="text-xs font-semibold tracking-widest uppercase text-zinc-500">
                Simulation Config
              </h2>
            </div>
            
            <form onSubmit={handleSubmit} className="space-y-5 flex-grow flex flex-col justify-between">
              <div className="space-y-4">
                
                <div className="space-y-1.5">
                  <label className="text-[11px] font-semibold tracking-wider text-zinc-500 uppercase block">Country</label>
                  <select 
                    className="w-full bg-zinc-50 border border-zinc-200 rounded-lg px-3 py-2.5 text-sm text-zinc-900 focus:border-zinc-400 focus:ring-1 focus:ring-zinc-400 outline-none transition-all"
                    value={formData.country}
                    onChange={(e) => {
                      setFormData({...formData, country: e.target.value});
                      addLog(`Country changed to ${e.target.value}`);
                    }}
                  >
                    {countries.map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-[11px] font-semibold tracking-wider text-zinc-500 uppercase block">Disaster Type</label>
                  <select 
                    className="w-full bg-zinc-50 border border-zinc-200 rounded-lg px-3 py-2.5 text-sm text-zinc-900 focus:border-zinc-400 focus:ring-1 focus:ring-zinc-400 outline-none transition-all"
                    value={formData.disaster_type}
                    onChange={(e) => {
                      setFormData({...formData, disaster_type: e.target.value});
                      addLog(`Disaster changed to ${e.target.value}`);
                    }}
                  >
                    {disasters.map(d => <option key={d} value={d}>{d}</option>)}
                  </select>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-[11px] font-semibold tracking-wider text-zinc-500 uppercase block">Month</label>
                    <select 
                      className="w-full bg-zinc-50 border border-zinc-200 rounded-lg px-3 py-2.5 text-sm text-zinc-900 focus:border-zinc-400 focus:ring-1 focus:ring-zinc-400 outline-none transition-all"
                      value={formData.month}
                      onChange={(e) => setFormData({...formData, month: Number(e.target.value)})}
                    >
                      {months.map(m => <option key={m} value={m}>{m}</option>)}
                    </select>
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-[11px] font-semibold tracking-wider text-zinc-500 uppercase block">Year</label>
                    <input 
                      type="text"
                      maxLength={4}
                      className="w-full bg-zinc-50 border border-zinc-200 rounded-lg px-3 py-2.5 text-sm font-mono text-zinc-900 focus:border-zinc-400 focus:ring-1 focus:ring-zinc-400 outline-none transition-all"
                      value={formData.event_year}
                      onChange={(e) => {
                        let val = e.target.value.replace(/[^0-9]/g, '');
                        if (val.length === 4 && parseInt(val) > 2026) val = "2026";
                        setFormData({...formData, event_year: val});
                      }}
                    />
                  </div>
                </div>

                <div className="space-y-2 pt-2">
                  <div className="flex justify-between items-center text-[11px]">
                    <label className="font-semibold tracking-wider text-zinc-500 uppercase">
                      {getSeverityLabel(formData.disaster_type)}
                    </label>
                    <span className="font-mono font-medium text-zinc-900 bg-zinc-100 px-2 py-0.5 rounded border border-zinc-200">
                      {formData.severity}
                    </span>
                  </div>
                  <input 
                    type="range"
                    min="1" max="10" step="0.1"
                    className="w-full accent-zinc-900 cursor-pointer"
                    value={formData.severity}
                    onChange={(e) => setFormData({...formData, severity: Number(e.target.value)})}
                  />
                </div>

                <div className="space-y-1.5 pt-2">
                  <label className="text-[11px] font-semibold tracking-wider text-zinc-500 uppercase block">Contextual Details</label>
                  <textarea 
                    className="w-full bg-zinc-50 border border-zinc-200 rounded-lg px-3 py-3 text-sm text-zinc-900 focus:border-zinc-400 focus:ring-1 focus:ring-zinc-400 outline-none h-24 resize-none transition-all"
                    value={formData.query_text}
                    onChange={(e) => setFormData({...formData, query_text: e.target.value})}
                    placeholder="Describe specific scenario metrics..."
                  />
                </div>
              </div>

              {/* Execute Button */}
              <div className="pt-4 mt-auto">
                <button 
                  type="submit" 
                  disabled={isLoading}
                  className="w-full bg-zinc-900 hover:bg-zinc-800 text-white font-medium py-3 px-4 rounded-lg text-sm transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 cursor-pointer shadow-sm"
                >
                  {isLoading ? (
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : (
                    <>
                      Run Simulation
                    </>
                  )}
                </button>
              </div>

            </form>
            
            {/* Diagnostics console */}
            <div className="mt-5 pt-4 border-t border-zinc-100">
              <div className="bg-zinc-50 p-3 rounded-lg border border-zinc-200/60 max-h-[80px] overflow-y-auto space-y-1 text-[11px] font-mono text-zinc-500">
                {consoleLogs.map((log, idx) => (
                  <p key={idx} className={log.includes("failed") ? "text-red-500" : "text-zinc-500"}>
                    {log}
                  </p>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* COLUMN 2: CENTER STAGE / MAP CANVAS (Span 6) */}
        <div className="lg:col-span-6 flex flex-col min-h-[500px]">
          
          <div className="flex-grow w-full border border-zinc-200 rounded-xl overflow-hidden bg-white relative shadow-sm flex flex-col justify-end">
            
            {/* Outer Header Indicator */}
            <div className="absolute top-4 left-4 z-20 flex items-center gap-2 text-xs font-medium text-zinc-600 bg-white/90 border border-zinc-200 px-3 py-1.5 rounded-full shadow-sm backdrop-blur-md">
              <MapPin className="w-3.5 h-3.5" />
              Geospatial View
            </div>

            {isMounted && (
              <Map
                {...viewState}
                onMove={evt => setViewState(evt.viewState)}
                mapStyle="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
                style={{ width: "100%", height: "100%" }}
              >
                <NavigationControl position="top-right" />
                {results?.historical_context?.map((ctx: any, idx: number) => {
                  const baseCoords = countryCoords[formData.country] || { lat: 0, lng: 0, zoom: 3 };
                  // Generate deterministic pseudo-random offset within a realistic radius (~3 degrees)
                  const latOffset = Math.sin(idx * 12.9898 + ctx.similarity_score * 78.233) * 3.5;
                  const lngOffset = Math.cos(idx * 4.1414 + ctx.similarity_score * 43.232) * 3.5;
                  
                  return (
                    <Marker 
                      key={`marker-${idx}`} 
                      longitude={baseCoords.lng + lngOffset} 
                      latitude={baseCoords.lat + latOffset} 
                      anchor="center"
                    >
                      <div className="relative flex h-5 w-5 group">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-purple-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-5 w-5 bg-purple-600 border-2 border-white shadow-md flex items-center justify-center text-[8px] text-white font-bold">
                          {idx + 1}
                        </span>
                        
                        {/* Tooltip on hover */}
                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-32 bg-zinc-900 text-white text-[10px] p-2 rounded shadow-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
                          <p className="font-semibold text-purple-300">{(ctx.similarity_score * 100).toFixed(1)}% Match</p>
                          <p className="truncate opacity-80">{String(ctx.country).startsWith("http") ? "ReliefWeb Event" : String(ctx.country)}</p>
                          <p className="opacity-80">Year: {ctx.event_year || "HIST"}</p>
                        </div>
                      </div>
                    </Marker>
                  );
                })}
              </Map>
            )}

            {/* INTEGRATED HUD FOOTER BAR: XGBOOST MATH ENGINE RESULTS */}
            <div className="absolute bottom-4 left-4 right-4 z-10 flex gap-4">
              
              {/* ESTIMATED AFFECTED POPULATION */}
              <div className="flex-1 bg-white/95 backdrop-blur-md border border-zinc-200 rounded-xl p-4 shadow-sm flex flex-col justify-center relative overflow-hidden group">
                <div className="w-1 h-full absolute left-0 top-0 bg-emerald-500 rounded-l-xl opacity-80" />
                <p className="text-[11px] text-zinc-500 font-semibold uppercase tracking-wider mb-1 flex items-center gap-1.5">
                  Affected Population
                </p>
                <p className="text-xl font-mono font-medium text-zinc-900">
                  {results ? formatNumber(results.predictions.estimated_affected_population) : "—"}
                </p>
              </div>

              {/* ESTIMATED ECONOMIC DAMAGE */}
              <div className="flex-1 bg-white/95 backdrop-blur-md border border-zinc-200 rounded-xl p-4 shadow-sm flex flex-col justify-center relative overflow-hidden group">
                <div className="w-1 h-full absolute left-0 top-0 bg-zinc-900 rounded-l-xl opacity-80" />
                <p className="text-[11px] text-zinc-500 font-semibold uppercase tracking-wider mb-1 flex items-center gap-1.5">
                  Economic Impact
                </p>
                <p className="text-xl font-mono font-medium text-zinc-900">
                  {results ? (
                    <>
                      <span className="text-zinc-400 mr-1">$</span>
                      {formatNumber(results.predictions.estimated_damage_usd_thousands)}K
                    </>
                  ) : (
                    "—"
                  )}
                </p>
              </div>

            </div>

            {/* Error alerts floating over map */}
            {error && (
              <div className="absolute top-16 left-4 right-4 z-10 bg-red-50 border border-red-200 p-3 rounded-lg flex items-start gap-3 shadow-sm">
                <AlertTriangle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
                <div>
                  <p className="text-red-800 font-semibold text-sm">Simulation Error</p>
                  <p className="text-xs text-red-600 mt-0.5">{error}</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* COLUMN 3: THE ORACLE / LLM BRIEFING (Span 3) */}
        <div className="lg:col-span-3 flex flex-col">
          <div className="bg-white border border-zinc-200 rounded-xl p-5 shadow-sm flex flex-col h-full relative overflow-hidden">

            <div className="flex items-center justify-between mb-4 pb-3 border-b border-zinc-100">
              <div className="flex items-center gap-2">
                <Database className="w-4 h-4 text-zinc-400" />
                <h2 className="text-xs font-semibold tracking-widest uppercase text-zinc-500">
                  Historical Context
                </h2>
              </div>
            </div>

            <div className="flex-grow space-y-4 overflow-y-auto max-h-[calc(100vh-250px)] pr-2">
              <p className="text-xs text-zinc-500 italic leading-relaxed mb-4">
                Displaying closest historical analogy from vector memory...
              </p>

              <AnimatePresence mode="wait">
                {!results ? (
                  <motion.div 
                    key="empty"
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                    className="h-full min-h-[250px] flex flex-col items-center justify-center p-6 text-center text-zinc-400 gap-3 border border-dashed border-zinc-200 rounded-lg bg-zinc-50"
                  >
                    <Search className="w-5 h-5 opacity-50" />
                    <p className="text-xs">No simulation active</p>
                  </motion.div>
                ) : (
                  <motion.div 
                    key="results"
                    initial="hidden" animate="show"
                    variants={{
                      hidden: { opacity: 0 },
                      show: {
                        opacity: 1,
                        transition: { staggerChildren: 0.1 }
                      }
                    }}
                    className="space-y-4"
                  >
                    {results.historical_context.length === 0 ? (
                      <div className="text-xs p-4 text-zinc-500 bg-zinc-50 border border-zinc-200 rounded-lg text-center">
                        No recorded analogues found.
                      </div>
                    ) : (
                      results.historical_context.map((ctx: any, idx: number) => (
                        <motion.div 
                          key={idx}
                          variants={{
                            hidden: { opacity: 0, y: 10 },
                            show: { opacity: 1, y: 0 }
                          }}
                          className="bg-white border border-zinc-200 rounded-xl p-4 shadow-sm hover:shadow transition-all duration-300"
                        >
                          <div className="flex items-center justify-between border-b border-zinc-100 pb-3 mb-3">
                            <div className="flex flex-col gap-1">
                              <span className="text-xs font-semibold text-zinc-900 uppercase">
                                {String(ctx.country).startsWith("http") ? "ReliefWeb" : String(ctx.country)}
                              </span>
                              <span className="text-[10px] font-medium text-zinc-500 uppercase">
                                {String(ctx.disaster_type).match(/^\d+$/) ? `ID:${ctx.disaster_type}` : String(ctx.disaster_type)}
                              </span>
                            </div>
                            <div className="flex flex-col items-end gap-1">
                              <div className="flex items-center gap-1 text-zinc-500 text-[10px] font-medium">
                                <Clock className="w-3 h-3" />
                                {ctx.event_year || "HIST"}
                              </div>
                              <span className="text-zinc-600 bg-zinc-100 px-1.5 py-0.5 rounded text-[10px] font-mono font-medium">
                                {(ctx.similarity_score * 100).toFixed(0)}% Match
                              </span>
                            </div>
                          </div>
                          
                          <p className="text-xs text-zinc-600 leading-relaxed">
                            {ctx.narrative_preview}
                          </p>
                        </motion.div>
                      ))
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
            
          </div>
        </div>

      </main>
    </div>
  );
}
